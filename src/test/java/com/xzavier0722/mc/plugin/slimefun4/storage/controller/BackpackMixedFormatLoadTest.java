package com.xzavier0722.mc.plugin.slimefun4.storage.controller;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.common.DataScope;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.FieldKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.RecordKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.RecordSet;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.ScopeKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.util.ItemStackDataCodec;
import io.github.thebusybiscuit.slimefun4.api.player.PlayerBackpack;
import java.io.ByteArrayOutputStream;
import java.lang.reflect.InvocationTargetException;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Types;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.bukkit.NamespacedKey;
import org.bukkit.inventory.ItemStack;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.util.io.BukkitObjectOutputStream;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.ServerMock;

/** Real loader/codec with SQLite reads; write submissions are counted, not executed by a worker. */
class BackpackMixedFormatLoadTest {
    private ServerMock server;
    private InventoryReadTestPlugin fixture;
    private StoredProfiles profiles;

    @TempDir
    Path directory;

    enum Encoding {
        NATIVE_BINARY,
        CURRENT_BASE64_BYTES,
        CURRENT_BASE64_TEXT,
        LEGACY_BASE64_BYTES,
        LEGACY_BASE64_TEXT,
        LEGACY_MIME_TEXT;

        Object valid(ItemStack item) throws Exception {
            byte[] payload = name().startsWith("LEGACY") ? legacyObject(item) : ItemStackDataCodec.serialize(item);
            return wrap(payload);
        }

        Object corrupt() {
            byte[] payload = name().startsWith("LEGACY")
                    ? new byte[] {(byte) 0xac, (byte) 0xed, 0, 5}
                    : new byte[] {'S', 'F', '2', 0};
            return wrap(payload);
        }

        private Object wrap(byte[] payload) {
            return switch (this) {
                case NATIVE_BINARY -> payload;
                case CURRENT_BASE64_BYTES, LEGACY_BASE64_BYTES -> Base64.getEncoder().encode(payload);
                case CURRENT_BASE64_TEXT, LEGACY_BASE64_TEXT -> Base64.getEncoder().encodeToString(payload);
                case LEGACY_MIME_TEXT -> Base64.getMimeEncoder(32, new byte[] {'\r', '\n'})
                        .encodeToString(payload);
            };
        }
    }

    @BeforeEach
    void setUp() throws Exception {
        server = MockBukkit.mock();
        server.addSimpleWorld("old_world");
        fixture = new InventoryReadTestPlugin(server);
        profiles = new StoredProfiles(directory.resolve("backpacks.db"));
    }

    @AfterEach
    void tearDown() throws Exception {
        try {
            if (profiles != null) {
                profiles.close();
            }
        } finally {
            try {
                if (fixture != null) {
                    fixture.close();
                }
            } finally {
                MockBukkit.unmock();
            }
        }
    }

    @ParameterizedTest
    @EnumSource(Encoding.class)
    void mixedRowsRetainIdentityBytesAndStorageTypesAcrossDatabaseReopen(Encoding encoding) throws Exception {
        UUID id = UUID.randomUUID();
        ItemStack expected = existingItem();
        profiles.put(id, "0", ItemStackDataCodec.serialize(expected));
        profiles.put(id, "1", encoding.valid(expected));
        profiles.put(id, "2", Encoding.LEGACY_BASE64_TEXT.valid(expected));
        profiles.put(id, "3", Encoding.CURRENT_BASE64_BYTES.valid(expected));
        profiles.put(id, "4", null);
        profiles.put(id, "5", " \r\n");
        profiles.put(id, "6", new byte[0]);
        List<String> before = profiles.snapshot();

        for (int read = 0; read < 2; read++) {
            ItemStack[] contents = profiles.readNormally(id);
            assertEquals(9, contents.length);
            for (int slot = 0; slot < 4; slot++) {
                assertItem(expected, contents[slot]);
            }
            for (int slot = 4; slot < 9; slot++) {
                assertNull(contents[slot]);
            }
            assertFalse(profiles.getInventoryRecoverySnapshot().hasEntries());
            assertEquals(0, profiles.submittedWrites);
            assertEquals(before, profiles.snapshot(), "Loading must not normalize or rewrite stored rows");
            profiles.reopen();
        }
    }

    @ParameterizedTest
    @EnumSource(Encoding.class)
    void corruptMixedRowBlocksOnlyItsBackpackAndRetainsRowsUntilExplicitRestore(Encoding encoding) throws Exception {
        UUID heldId = UUID.randomUUID();
        UUID healthyId = UUID.randomUUID();
        ItemStack expected = existingItem();
        profiles.put(heldId, "0", ItemStackDataCodec.serialize(expected));
        profiles.put(heldId, "4", encoding.valid(expected));
        profiles.put(heldId, "8", encoding.corrupt());
        profiles.put(healthyId, "0", Encoding.LEGACY_BASE64_TEXT.valid(expected));
        List<String> before = profiles.snapshot();

        assertThrows(IllegalStateException.class, () -> profiles.readNormally(heldId));
        assertEquals(1, profiles.getInventoryRecoverySnapshot().totalEntries());
        PlayerBackpack unverified = new PlayerBackpack(server.addPlayer(), heldId, "Held backpack", 1, 9, null);
        assertTrue(profiles.saveBackpackInventoryAsync(unverified).isCompletedExceptionally());
        assertEquals(0, profiles.submittedWrites, "Failed reads must not authorize empty saves or deletes");
        assertEquals(before, profiles.snapshot());

        assertItem(expected, profiles.readNormally(healthyId)[0]);
        assertEquals(
                1,
                profiles.getInventoryRecoverySnapshot().totalEntries(),
                "Loading a different backpack must not clear the original hold");
        assertTrue(profiles.saveBackpackInventoryAsync(unverified).isCompletedExceptionally());
        profiles.reopen();
        assertThrows(IllegalStateException.class, () -> profiles.readNormally(heldId));
        assertEquals(before, profiles.snapshot());
        assertEquals(0, profiles.submittedWrites);

        // Explicit fixture restore only: normal loading must never perform this replacement.
        profiles.put(heldId, "8", encoding.valid(expected));
        List<String> restoredRows = profiles.snapshot();
        ItemStack[] recovered = profiles.readNormally(heldId);
        for (int slot : new int[] {0, 4, 8}) {
            assertItem(expected, recovered[slot]);
        }
        assertFalse(profiles.getInventoryRecoverySnapshot().hasEntries());
        assertEquals(restoredRows, profiles.snapshot());
        assertEquals(0, profiles.submittedWrites, "A successful recovery read must remain read-only");
        PlayerBackpack recoveredBackpack =
                new PlayerBackpack(server.addPlayer(), heldId, "Recovered backpack", 1, 9, recovered);
        CompletableFuture<Void> saved = profiles.saveBackpackInventoryAsync(recoveredBackpack);
        assertTrue(saved.isDone(), "The fixture completes every intercepted write submission immediately");
        assertFalse(saved.isCompletedExceptionally(), "Complete recovery must release the save hold");
        saved.join();
        assertTrue(profiles.submittedWrites > 0, "The recovered save must reach the write submission boundary");
        int writesAfterRecoverySave = profiles.submittedWrites;
        assertItem(expected, profiles.readNormally(healthyId)[0]);
        assertEquals(writesAfterRecoverySave, profiles.submittedWrites, "Reading another backpack must remain read-only");
        assertEquals(restoredRows, profiles.snapshot());
    }

    private static ItemStack existingItem() {
        ItemStack item = StoredInventoryReaderTest.item();
        var meta = item.getItemMeta();
        meta.getPersistentDataContainer()
                .set(
                        NamespacedKey.fromString("slimefun:b_uuid"),
                        PersistentDataType.STRING,
                        "1f017f3a-8442-4ef2-9fba-456789abcdef");
        meta.getPersistentDataContainer()
                .set(
                        NamespacedKey.fromString("oldaddon:owner_uuid"),
                        PersistentDataType.STRING,
                        "2f017f3a-8442-4ef2-9fba-456789abcdef");
        item.setItemMeta(meta);
        return item;
    }

    private static void assertItem(ItemStack expected, ItemStack actual) {
        assertNotNull(actual);
        assertEquals(expected.getType(), actual.getType());
        assertEquals(expected.getAmount(), actual.getAmount());
        assertEquals(expected.getItemMeta(), actual.getItemMeta());
    }

    @SuppressWarnings("deprecation") // Generates old-format fixtures; never used by production writers.
    private static byte[] legacyObject(ItemStack item) throws Exception {
        try (var bytes = new ByteArrayOutputStream();
                var output = new BukkitObjectOutputStream(bytes)) {
            output.writeObject(item);
            output.flush();
            return bytes.toByteArray();
        }
    }

    private static final class StoredProfiles extends ProfileDataController implements AutoCloseable {
        private final String jdbc;
        private Connection connection;
        private int submittedWrites;

        private StoredProfiles(Path database) throws SQLException {
            jdbc = "jdbc:sqlite:" + database;
            connection = DriverManager.getConnection(jdbc);
            try (var statement = connection.createStatement()) {
                statement.execute("CREATE TABLE saved_inventory "
                        + "(backpack TEXT, slot TEXT, item BLOB, PRIMARY KEY(backpack, slot))");
            }
        }

        private void put(UUID id, String slot, Object raw) throws SQLException {
            try (var statement = connection.prepareStatement("INSERT OR REPLACE INTO saved_inventory VALUES (?, ?, ?)")) {
                statement.setString(1, id.toString());
                statement.setString(2, slot);
                if (raw instanceof byte[] bytes) {
                    statement.setBytes(3, bytes);
                } else if (raw instanceof String text) {
                    statement.setString(3, text);
                } else if (raw == null) {
                    statement.setNull(3, Types.BLOB);
                } else {
                    throw new IllegalArgumentException("Unexpected fixture representation");
                }
                statement.executeUpdate();
            }
        }

        private List<String> snapshot() throws SQLException {
            var result = new ArrayList<String>();
            try (var statement = connection.createStatement();
                    var rows = statement.executeQuery(
                            "SELECT backpack,slot,typeof(item),hex(item) FROM saved_inventory ORDER BY backpack,slot")) {
                while (rows.next()) {
                    result.add(rows.getString(1) + "/" + rows.getString(2) + "/" + rows.getString(3) + "/"
                            + rows.getString(4));
                }
            }
            return result;
        }

        private void reopen() throws SQLException {
            connection.close();
            connection = DriverManager.getConnection(jdbc);
        }

        private ItemStack[] readNormally(UUID id) throws Exception {
            var method = ProfileDataController.class.getDeclaredMethod("getBackpackInv", String.class, int.class);
            method.setAccessible(true);
            try {
                return (ItemStack[]) method.invoke(this, id.toString(), 9);
            } catch (InvocationTargetException failure) {
                if (failure.getCause() instanceof RuntimeException runtime) {
                    throw runtime;
                }
                throw failure;
            }
        }

        @Override
        protected List<RecordSet> getData(RecordKey key) {
            assertEquals(DataScope.BACKPACK_INVENTORY, key.getScope());
            String id = key.getConditions().stream()
                    .filter(condition -> condition.getFirstValue() == FieldKey.BACKPACK_ID)
                    .map(condition -> condition.getSecondValue())
                    .findFirst()
                    .orElseThrow();
            var result = new ArrayList<RecordSet>();
            try (var statement = connection.prepareStatement(
                    "SELECT slot,item FROM saved_inventory WHERE backpack=? ORDER BY slot")) {
                statement.setString(1, id);
                try (var rows = statement.executeQuery()) {
                    while (rows.next()) {
                        RecordSet row = StoredInventoryReaderTest.row(rows.getString(1), rows.getObject(2));
                        row.readonly();
                        result.add(row);
                    }
                }
            } catch (SQLException failure) {
                throw new IllegalStateException(failure);
            }
            return result;
        }

        @Override
        protected CompletableFuture<Void> scheduleWriteTaskWithCompletion(
                ScopeKey scope, RecordKey key, RecordSet data, boolean serial) {
            submittedWrites++;
            return CompletableFuture.completedFuture(null);
        }

        @Override
        protected CompletableFuture<Void> scheduleDeleteTaskWithCompletion(
                ScopeKey scope, RecordKey key, boolean serial) {
            submittedWrites++;
            return CompletableFuture.completedFuture(null);
        }

        @Override
        public void close() throws Exception {
            try {
                var field = ProfileDataController.class.getDeclaredField("backpackCache");
                field.setAccessible(true);
                ((BackpackCache) field.get(this)).clean();
            } finally {
                connection.close();
            }
        }
    }
}
