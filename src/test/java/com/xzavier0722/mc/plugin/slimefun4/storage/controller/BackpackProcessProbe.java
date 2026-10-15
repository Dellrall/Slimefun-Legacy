package com.xzavier0722.mc.plugin.slimefun4.storage.controller;

import static com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon.SqlConstants.FIELD_BACKPACK_ID;
import static com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon.SqlConstants.FIELD_INVENTORY_ITEM;
import static com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon.SqlConstants.FIELD_INVENTORY_SLOT;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon.SqlUtils;
import com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlite.SqliteAdapter;
import com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlite.SqliteConfig;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.BackpackInventoryBatch;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.DataScope;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.DataType;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.FieldKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.RecordKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.RecordSet;
import com.xzavier0722.mc.plugin.slimefun4.storage.util.DataUtils;
import io.github.thebusybiscuit.slimefun4.api.player.PlayerBackpack;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.DriverManager;
import java.util.Base64;
import java.util.Map;
import java.util.Properties;
import java.util.TreeMap;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.bukkit.inventory.ItemStack;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.ServerMock;

/** Test-only child entry point. Runtime.halt is never called in a JUnit worker or a server process. */
public final class BackpackProcessProbe {
    private static final UUID OWNER = UUID.fromString("db296f16-7cef-4c10-b81b-ef27867aa00a");
    private static final UUID TARGET = UUID.fromString("6e6a03bc-7d38-41c3-98e3-98400eff592a");
    private static final UUID HEALTHY = UUID.fromString("e8369ebe-c516-4d9e-aed6-0cc6e941c7b3");
    private static final String NAME = "Existing process-test backpack";
    private static final int WAIT_SECONDS = 20;

    private BackpackProcessProbe() {}

    public static void main(String[] arguments) {
        try {
            if (arguments.length != 4) {
                throw new IllegalArgumentException("Expected temporary directory, phase, boundary and nonce");
            }
            Path directory = Path.of(arguments[0]);
            String phase = arguments[1];
            var boundary = BackpackProcessRestartTest.Boundary.valueOf(arguments[2]);
            String nonce = UUID.fromString(arguments[3]).toString();
            try (var storage = new Storage(directory)) {
                switch (phase) {
                    case "SEED" -> storage.seed(directory);
                    case "VERIFY" -> storage.verify(directory, boundary);
                    case "WRITE" -> {
                        storage.write(boundary);
                        if (boundary != BackpackProcessRestartTest.Boundary.CLEAN_SHUTDOWN) {
                            marker(nonce, phase);
                            Runtime.getRuntime().halt(boundary.exitCode);
                            throw new AssertionError("Runtime.halt returned");
                        }
                    }
                    default -> throw new IllegalArgumentException("Unknown phase " + phase);
                }
            }
            marker(nonce, phase);
            System.exit(0);
        } catch (Throwable failure) {
            failure.printStackTrace(System.err);
            System.exit(1);
        }
    }

    private static void marker(String nonce, String phase) {
        System.out.println("BACKPACK_PROCESS:" + nonce + ":" + phase + ":"
                + ProcessHandle.current().pid());
        System.out.flush();
    }

    private static ItemStack item(int amount) {
        ItemStack item = StoredInventoryReaderTest.item();
        item.setAmount(amount);
        return item;
    }

    private static Field field(Class<?> type, String name) throws Exception {
        Field field = type.getDeclaredField(name);
        field.setAccessible(true);
        return field;
    }

    private static final class Storage implements AutoCloseable {
        private final ServerMock server;
        private final InventoryReadTestPlugin fixture;
        private final ProbeAdapter adapter;
        private final ProbeController controller;
        private final SqliteConfig config;

        private Storage(Path directory) throws Exception {
            server = MockBukkit.mock();
            server.addSimpleWorld("old_world");
            fixture = new InventoryReadTestPlugin(server);
            config = new SqliteConfig(directory.resolve("backpack-process.db").toString(), 3);
            adapter = new ProbeAdapter();
            adapter.prepare(config);
            adapter.initStorage(DataType.PLAYER_PROFILE);
            controller = new ProbeController(adapter);
        }

        private void seed(Path directory) throws Exception {
            var profileKey = new RecordKey(DataScope.PLAYER_PROFILE);
            profileKey.addCondition(FieldKey.PLAYER_UUID, OWNER.toString());
            var profile = new RecordSet();
            profile.put(FieldKey.PLAYER_UUID, OWNER.toString());
            profile.put(FieldKey.PLAYER_NAME, "ProcessFixtureOwner");
            profile.put(FieldKey.PLAYER_BACKPACK_NUM, "2");
            adapter.seed(profileKey, profile);
            seedBackpack(TARGET, 1);
            seedBackpack(HEALTHY, 2);
            Properties snapshot = new Properties();
            snapshot.putAll(rows());
            try (var stream = Files.newOutputStream(directory.resolve("seed-rows.properties"))) {
                snapshot.store(stream, "Disposable fixture rows; no player data");
            }
            assertEquals(4, snapshot.size());
        }

        private void seedBackpack(UUID id, int number) {
            var key = new RecordKey(DataScope.BACKPACK_PROFILE);
            key.addCondition(FieldKey.BACKPACK_ID, id.toString());
            var data = new RecordSet();
            data.put(FieldKey.BACKPACK_ID, id.toString());
            data.put(FieldKey.PLAYER_UUID, OWNER.toString());
            data.put(FieldKey.BACKPACK_NUMBER, Integer.toString(number));
            data.put(FieldKey.BACKPACK_SIZE, "9");
            data.put(FieldKey.BACKPACK_NAME, DataUtils.profileDataBase64(NAME));
            adapter.seed(key, data);
            for (int slot : new int[] {0, 8}) {
                var slotKey = new RecordKey(DataScope.BACKPACK_INVENTORY);
                slotKey.addCondition(FieldKey.BACKPACK_ID, id.toString());
                slotKey.addCondition(FieldKey.INVENTORY_SLOT, Integer.toString(slot));
                var slotData = new RecordSet();
                slotData.put(FieldKey.BACKPACK_ID, id.toString());
                slotData.put(FieldKey.INVENTORY_SLOT, Integer.toString(slot));
                slotData.put(FieldKey.INVENTORY_ITEM, item(23));
                adapter.seed(slotKey, slotData);
            }
        }

        private void write(BackpackProcessRestartTest.Boundary boundary) throws Exception {
            PlayerBackpack pack = load(TARGET, 1);
            adapter.boundary = boundary;
            pack.getInventory().setItem(0, item(7));
            var saved = controller.saveBackpackInventoryAsync(pack);
            switch (boundary) {
                case BEFORE_WRITE, AFTER_WRITE_BEFORE_ACK -> {
                    assertTrue(adapter.entered.await(WAIT_SECONDS, TimeUnit.SECONDS));
                    assertFalse(saved.isDone(), "The requested write must still be pending at the interruption");
                    assertEquals(1, controller.getPendingBackpackSaveChainCount());
                    assertEquals(1, adapter.writes.get());
                    assertEquals(0, adapter.deletes.get());
                }
                case AFTER_ACK, CLEAN_SHUTDOWN -> {
                    saved.get(WAIT_SECONDS, TimeUnit.SECONDS);
                    assertEquals(1, adapter.writes.get());
                    assertEquals(0, adapter.deletes.get());
                    assertTrue(pack.getSnapshot()
                            .getChangedSlots(pack.getInventory().getContents())
                            .isEmpty());
                }
            }
        }

        private void verify(Path directory, BackpackProcessRestartTest.Boundary boundary) throws Exception {
            Properties seed = new Properties();
            try (var stream = Files.newInputStream(directory.resolve("seed-rows.properties"))) {
                seed.load(stream);
            }
            Map<String, String> beforeRead = rows();
            assertEquals(seed.stringPropertyNames(), beforeRead.keySet());
            String edited = TARGET + ":0";
            for (String key : seed.stringPropertyNames()) {
                if (!key.equals(edited) || boundary == BackpackProcessRestartTest.Boundary.BEFORE_WRITE) {
                    assertEquals(seed.getProperty(key), beforeRead.get(key), "Unchanged SQL type and bytes for " + key);
                } else {
                    assertNotEquals(seed.getProperty(key), beforeRead.get(key));
                }
            }
            int amount = boundary == BackpackProcessRestartTest.Boundary.BEFORE_WRITE ? 23 : 7;
            PlayerBackpack target = load(TARGET, 1);
            PlayerBackpack healthy = load(HEALTHY, 2);
            assertContents(target, amount);
            assertContents(healthy, 23);
            controller.saveBackpackInventoryAsync(target).get(WAIT_SECONDS, TimeUnit.SECONDS);
            controller.saveBackpackInventoryAsync(healthy).get(WAIT_SECONDS, TimeUnit.SECONDS);
            assertEquals(0, adapter.writes.get(), "Fresh-process reads and unchanged saves must not rewrite items");
            assertEquals(0, adapter.deletes.get());
            assertEquals(beforeRead, rows());
        }

        private PlayerBackpack load(UUID id, int number) {
            PlayerBackpack pack = controller.getBackpack(id.toString());
            assertNotNull(pack);
            assertEquals(id, pack.getUniqueId());
            assertEquals(OWNER, pack.getOwner().getUniqueId());
            assertEquals(number, pack.getId());
            assertEquals(9, pack.getSize());
            assertEquals(NAME, pack.getName());
            return pack;
        }

        private static void assertContents(PlayerBackpack pack, int firstAmount) {
            for (int slot = 0; slot < 9; slot++) {
                ItemStack actual = pack.getInventory().getItem(slot);
                if (slot == 0 || slot == 8) {
                    ItemStack expected = item(slot == 0 ? firstAmount : 23);
                    assertNotNull(actual);
                    assertEquals(expected.getType(), actual.getType());
                    assertEquals(expected.getAmount(), actual.getAmount());
                    assertEquals(expected.getItemMeta(), actual.getItemMeta());
                } else {
                    assertNull(actual);
                }
            }
        }

        private Map<String, String> rows() throws Exception {
            Map<String, String> result = new TreeMap<>();
            String sql = "SELECT " + FIELD_BACKPACK_ID + "," + FIELD_INVENTORY_SLOT + ",typeof("
                    + FIELD_INVENTORY_ITEM + ")," + FIELD_INVENTORY_ITEM + " FROM "
                    + SqlUtils.mapTable(DataScope.BACKPACK_INVENTORY);
            try (var connection = DriverManager.getConnection(config.jdbcUrl());
                    var statement = connection.createStatement();
                    var rows = statement.executeQuery(sql)) {
                while (rows.next()) {
                    String key = rows.getString(1) + ":" + rows.getInt(2);
                    assertNull(result.put(
                            key, rows.getString(3) + ":" + Base64.getEncoder().encodeToString(rows.getBytes(4))));
                }
            }
            return result;
        }

        @Override
        public void close() throws Exception {
            adapter.release.countDown();
            try {
                controller.shutdown();
                assertTrue(controller.wasLastShutdownClean());
            } finally {
                try {
                    controller.closeFixture();
                } finally {
                    try {
                        adapter.shutdown();
                    } finally {
                        fixture.close();
                        MockBukkit.unmock();
                    }
                }
            }
        }
    }

    private static final class ProbeController extends ProfileDataController {
        private ProbeController(SqliteAdapter adapter) throws Exception {
            field(ADataController.class, "dataAdapter").set(this, adapter);
            readExecutor = Executors.newSingleThreadExecutor();
            writeExecutor = Executors.newFixedThreadPool(2);
            callbackExecutor = Executors.newSingleThreadExecutor();
        }

        private void closeFixture() throws Exception {
            readExecutor.shutdownNow();
            callbackExecutor.shutdownNow();
            writeExecutor.shutdownNow();
            assertTrue(writeExecutor.awaitTermination(WAIT_SECONDS, TimeUnit.SECONDS));
            ((BackpackCache) field(ProfileDataController.class, "backpackCache").get(this)).clean();
        }
    }

    private static final class ProbeAdapter extends SqliteAdapter {
        private final CountDownLatch entered = new CountDownLatch(1);
        private final CountDownLatch release = new CountDownLatch(1);
        private final AtomicInteger writes = new AtomicInteger();
        private final AtomicInteger deletes = new AtomicInteger();
        private volatile BackpackProcessRestartTest.Boundary boundary;

        private void seed(RecordKey key, RecordSet data) {
            super.setData(key, data);
        }

        @Override
        public void saveBackpackInventory(BackpackInventoryBatch batch) {
            batch.slots().forEach(slot -> {
                if (slot.payload() == null) {
                    deletes.incrementAndGet();
                } else {
                    writes.incrementAndGet();
                }
            });
            if (boundary == BackpackProcessRestartTest.Boundary.BEFORE_WRITE) {
                block();
            }
            super.saveBackpackInventory(batch);
            if (boundary == BackpackProcessRestartTest.Boundary.AFTER_WRITE_BEFORE_ACK) {
                block();
            }
        }

        private void block() {
            entered.countDown();
            try {
                assertTrue(release.await(WAIT_SECONDS, TimeUnit.SECONDS), "Child writer boundary was not released");
            } catch (InterruptedException failure) {
                Thread.currentThread().interrupt();
                throw new AssertionError("Child writer interrupted before deliberate halt", failure);
            }
        }
    }
}
