package com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.adapter.IDataSourceAdapter;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.BackpackInventoryBatch;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Stream;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Real SQL commit/rollback checks plus explicit, deterministic driver-fault simulations. */
class SqlBackpackInventoryTransactionTest {
    private static final String TARGET = "11111111-2222-4333-8444-555555555555";
    private static final String OTHER = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
    private static final byte[] ITEM = new byte[] {'S', 'F', '2', 0, 23, -1, 42};

    @TempDir
    Path directory;

    @Test
    void batchOwnsPayloadsAndRejectsAmbiguousSlots() {
        byte[] supplied = ITEM.clone();
        var slots = new ArrayList<BackpackInventoryBatch.Slot>();
        slots.add(new BackpackInventoryBatch.Slot(1, supplied));
        var batch = new BackpackInventoryBatch(TARGET, slots);
        supplied[0] = 0;
        slots.clear();
        byte[] exported = batch.slots().getFirst().payload();
        exported[0] = 0;
        assertArrayEquals(ITEM, batch.slots().getFirst().payload());
        assertThrows(UnsupportedOperationException.class, () -> batch.slots().clear());
        assertThrows(
                IllegalArgumentException.class,
                () -> new BackpackInventoryBatch(
                        TARGET,
                        List.of(new BackpackInventoryBatch.Slot(1, null), new BackpackInventoryBatch.Slot(1, ITEM))));
        assertThrows(IllegalArgumentException.class, () -> new BackpackInventoryBatch("not-a-uuid", List.of()));
        assertThrows(IllegalArgumentException.class, () -> new BackpackInventoryBatch.Slot(54, ITEM));
        assertThrows(IllegalArgumentException.class, () -> new BackpackInventoryBatch.Slot(-1, ITEM));
        assertThrows(IllegalArgumentException.class, () -> new BackpackInventoryBatch.Slot(0, new byte[0]));
    }

    @Test
    void oldCustomAdaptersRefuseWithoutNonAtomicFallback() {
        var calls = new AtomicInteger();
        IDataSourceAdapter<?> adapter = (IDataSourceAdapter<?>) Proxy.newProxyInstance(
                IDataSourceAdapter.class.getClassLoader(),
                new Class<?>[] {IDataSourceAdapter.class},
                (proxy, method, args) -> {
                    if (method.isDefault()) {
                        return InvocationHandler.invokeDefault(proxy, method, args);
                    }
                    calls.incrementAndGet();
                    throw new AssertionError("An unsupported atomic save called a legacy adapter method");
                });
        assertThrows(UnsupportedOperationException.class, () -> adapter.saveBackpackInventory(move()));
        assertEquals(0, calls.get());
    }

    @Test
    void acknowledgedMoveAndExactReplayPreserveOpaqueBytesAfterConnectionReopen() throws Exception {
        Path file = directory.resolve("reopen.db");
        try (var connection = open(file)) {
            create(connection, "");
            SqlBackpackInventoryTransaction.execute(connection, "", move());
            assertMoved(connection, "");
            assertTrue(connection.getAutoCommit());
        }
        try (var connection = open(file)) {
            var before = rows(connection, "");
            SqlBackpackInventoryTransaction.execute(connection, "", move());
            assertEquals(before, rows(connection, ""));
            assertMoved(connection, "");
        }
    }

    @ParameterizedTest
    @ValueSource(ints = {1, 2})
    void eitherStatementFailureRollsBackEverySlotAndAllowsAnExplicitRetry(int index) throws Exception {
        try (var connection = open(directory.resolve("statement-" + index + ".db"))) {
            create(connection, "");
            var before = rows(connection, "");
            var probe = new BackpackJdbcProbe();
            var statements = new AtomicInteger();
            probe.after = operation -> {
                if (statements.incrementAndGet() == index) throw new SQLException("injected statement failure");
            };
            assertThrows(
                    IllegalStateException.class,
                    () -> SqlBackpackInventoryTransaction.execute(probe.wrap(connection), "", move()));
            assertEquals(index, statements.get());
            assertEquals(before, rows(connection, ""));
            assertTrue(connection.getAutoCommit());
            SqlBackpackInventoryTransaction.execute(connection, "", move());
            assertMoved(connection, "");
        }
    }

    @Test
    void commitFailureRollsBackButLostAcknowledgementStillReportsFailure() throws Exception {
        try (var connection = open(directory.resolve("commit.db"))) {
            create(connection, "");
            var before = rows(connection, "");
            var probe = new BackpackJdbcProbe();
            probe.beforeCommit = () -> {
                throw new SQLException("before commit");
            };
            assertThrows(
                    IllegalStateException.class,
                    () -> SqlBackpackInventoryTransaction.execute(probe.wrap(connection), "", move()));
            assertEquals(before, rows(connection, ""));
            probe.beforeCommit = () -> {};
            probe.afterCommit = () -> {
                throw new SQLException("lost commit acknowledgement");
            };
            var failure = assertThrows(
                    IllegalStateException.class,
                    () -> SqlBackpackInventoryTransaction.execute(probe.wrap(connection), "", move()));
            assertTrue(failure.getMessage().contains("uncertain"));
            assertMoved(connection, "");
        }
    }

    @Test
    void unresolvedRollbackNeverRestoresAutoCommitOrAcknowledgesSuccess() throws Exception {
        try (var connection = open(directory.resolve("rollback.db"))) {
            create(connection, "");
            var resets = new AtomicInteger();
            var aborts = new AtomicInteger();
            Connection failing = (Connection) Proxy.newProxyInstance(
                    Connection.class.getClassLoader(), new Class<?>[] {Connection.class}, (proxy, method, args) -> {
                        switch (method.getName()) {
                            case "commit" -> throw new SQLException("commit failed");
                            case "rollback" -> throw new SQLException("rollback failed");
                            case "abort" -> {
                                aborts.incrementAndGet();
                                return null;
                            }
                            case "setAutoCommit" -> {
                                if (Boolean.TRUE.equals(args[0])) resets.incrementAndGet();
                            }
                        }
                        try {
                            return method.invoke(connection, args);
                        } catch (InvocationTargetException error) {
                            throw error.getCause();
                        }
                    });
            var failure = assertThrows(
                    IllegalStateException.class, () -> SqlBackpackInventoryTransaction.execute(failing, "", move()));
            assertEquals(0, resets.get());
            assertEquals(1, aborts.get());
            assertEquals(1, failure.getCause().getSuppressed().length);
            assertFalse(connection.getAutoCommit());
            // Only fixture cleanup resolves the driver failure simulated above.
            connection.rollback();
            connection.setAutoCommit(true);
            assertEquals(4, rows(connection, "").size());
        }
    }

    @Test
    void callerOwnedTransactionAndUnknownDatabaseAreRejectedBeforeMutation() throws Exception {
        try (var connection = open(directory.resolve("rejected.db"))) {
            create(connection, "");
            var before = rows(connection, "");
            connection.setAutoCommit(false);
            assertThrows(SQLException.class, () -> SqlBackpackInventoryTransaction.execute(connection, "", move()));
            assertFalse(connection.getAutoCommit());
            connection.rollback();
            connection.setAutoCommit(true);
            DatabaseMetaData metadata = (DatabaseMetaData) Proxy.newProxyInstance(
                    DatabaseMetaData.class.getClassLoader(),
                    new Class<?>[] {DatabaseMetaData.class},
                    (proxy, method, args) -> {
                        if (method.getName().equals("getDatabaseProductName")) return "Unsupported database";
                        try {
                            return method.invoke(connection.getMetaData(), args);
                        } catch (InvocationTargetException error) {
                            throw error.getCause();
                        }
                    });
            Connection unknown = (Connection) Proxy.newProxyInstance(
                    Connection.class.getClassLoader(), new Class<?>[] {Connection.class}, (proxy, method, args) -> {
                        if (method.getName().equals("getMetaData")) return metadata;
                        try {
                            return method.invoke(connection, args);
                        } catch (InvocationTargetException error) {
                            throw error.getCause();
                        }
                    });
            assertThrows(SQLException.class, () -> SqlBackpackInventoryTransaction.execute(unknown, "", move()));
            assertThrows(
                    IllegalArgumentException.class,
                    () -> SqlBackpackInventoryTransaction.execute(connection, "unsafe;", move()));
            assertEquals(before, rows(connection, ""));
        }
    }

    @TestFactory
    Stream<DynamicTest> explicitlyConfiguredExternalDatabasesCommitAndRollback() {
        return Stream.of("MYSQL", "POSTGRES")
                .filter(database -> System.getenv("LEGACY_MIGRATION_" + database + "_URL") != null)
                .map(database -> DynamicTest.dynamicTest(
                        database + " backpack commit, rollback and uncertain acknowledgement", () -> {
                            String environment = "LEGACY_MIGRATION_" + database;
                            try (var connection = DriverManager.getConnection(
                                    System.getenv(environment + "_URL"),
                                    System.getenv(environment + "_USER"),
                                    System.getenv(environment + "_PASSWORD"))) {
                                String prefix =
                                        "bp_" + UUID.randomUUID().toString().replace("-", "") + "_";
                                try {
                                    create(connection, prefix);
                                    var before = rows(connection, prefix);
                                    var probe = new BackpackJdbcProbe();
                                    probe.after = operation -> {
                                        throw new SQLException("first statement failed");
                                    };
                                    assertThrows(
                                            IllegalStateException.class,
                                            () -> SqlBackpackInventoryTransaction.execute(
                                                    probe.wrap(connection), prefix, move()));
                                    assertEquals(before, rows(connection, prefix));
                                    probe.after = operation -> {};
                                    probe.afterCommit = () -> {
                                        throw new SQLException("lost acknowledgement");
                                    };
                                    assertThrows(
                                            IllegalStateException.class,
                                            () -> SqlBackpackInventoryTransaction.execute(
                                                    probe.wrap(connection), prefix, move()));
                                    assertMoved(connection, prefix);
                                    SqlBackpackInventoryTransaction.execute(connection, prefix, move());
                                    assertMoved(connection, prefix);
                                    if (database.equals("MYSQL")) {
                                        try (var statement = connection.createStatement()) {
                                            statement.execute(
                                                    "ALTER TABLE " + prefix + "backpack_inventory ENGINE=MyISAM");
                                        }
                                        var moved = rows(connection, prefix);
                                        assertThrows(
                                                SQLException.class,
                                                () -> SqlBackpackInventoryTransaction.execute(
                                                        connection, prefix, move()));
                                        assertEquals(moved, rows(connection, prefix));
                                    }
                                } finally {
                                    try (var statement = connection.createStatement()) {
                                        statement.execute("DROP TABLE IF EXISTS " + prefix + "backpack_inventory");
                                    }
                                }
                            }
                        }));
    }

    private static BackpackInventoryBatch move() {
        return new BackpackInventoryBatch(
                TARGET, List.of(new BackpackInventoryBatch.Slot(1, ITEM), new BackpackInventoryBatch.Slot(8, null)));
    }

    private static Connection open(Path file) throws SQLException {
        return DriverManager.getConnection("jdbc:sqlite:" + file);
    }

    private static void create(Connection connection, String prefix) throws SQLException {
        String product = connection.getMetaData().getDatabaseProductName();
        String binary = product.equalsIgnoreCase("PostgreSQL") ? "BYTEA" : "BLOB";
        String engine = product.equalsIgnoreCase("MySQL") ? " ENGINE=InnoDB" : "";
        try (var statement = connection.createStatement()) {
            statement.execute("CREATE TABLE " + prefix
                    + "backpack_inventory (b_id VARCHAR(64) NOT NULL, i_slot SMALLINT NOT NULL, i_item " + binary
                    + " NOT NULL, PRIMARY KEY (b_id, i_slot))" + engine);
        }
        try (var statement =
                connection.prepareStatement("INSERT INTO " + prefix + "backpack_inventory VALUES (?, ?, ?)")) {
            for (String id : List.of(TARGET, OTHER)) {
                for (int slot : new int[] {0, 8}) {
                    statement.setString(1, id);
                    statement.setInt(2, slot);
                    statement.setBytes(3, ITEM);
                    assertEquals(1, statement.executeUpdate());
                }
            }
        }
    }

    private static Map<String, String> rows(Connection connection, String prefix) throws SQLException {
        var result = new TreeMap<String, String>();
        try (var statement = connection.createStatement();
                var rows =
                        statement.executeQuery("SELECT b_id, i_slot, i_item FROM " + prefix + "backpack_inventory")) {
            while (rows.next()) {
                result.put(
                        rows.getString(1) + ":" + rows.getInt(2),
                        Base64.getEncoder().encodeToString(rows.getBytes(3)));
            }
        }
        return result;
    }

    private static void assertMoved(Connection connection, String prefix) throws SQLException {
        String payload = Base64.getEncoder().encodeToString(ITEM);
        assertEquals(
                Map.of(TARGET + ":0", payload, TARGET + ":1", payload, OTHER + ":0", payload, OTHER + ":8", payload),
                rows(connection, prefix));
    }
}
