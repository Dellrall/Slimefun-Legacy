package com.xzavier0722.mc.plugin.slimefun4.storage.controller;

import static com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon.SqlConstants.FIELD_BACKPACK_ID;
import static com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon.SqlConstants.FIELD_INVENTORY_ITEM;
import static com.xzavier0722.mc.plugin.slimefun4/storage/adapter/sqlcommon/SqlConstants.FIELD_INVENTORY_SLOT;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlcommon.SqlUtils;
import com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlite.SqliteAdapter;
import com.xzavier0722.mc.plugin.slimefun4.storage.adapter.sqlite.SqliteConfig;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.DataScope;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.DataType;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.FieldKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.RecordKey;
import com.xzavier0722.mc.plugin.slimefun4.storage.common.RecordSet;
import com.xzavier0722.mc.plugin.slimefun4.storage.util.DataUtils;
import io.github.thebusybiscuit.slimefun4.api.player.PlayerBackpack;
import java.lang.reflect.Field;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.LockSupport;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import org.bukkit.NamespacedKey;
import org.bukkit.inventory.ItemStack;
import org.bukkit.persistence.PersistentDataType;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.ServerMock;

/** Production save chain, tracked writer tasks and SQLite adapter; not a Minecraft process or power-loss test. */
class BackpackWriteCompletionTest {
    private static final long WAIT_SECONDS = 10;

    @TempDir
    Path directory;

    private ServerMock server;
    private InventoryReadTestPlugin fixture;
    private TestController controller;
    private FaultAdapter adapter;
    private SqliteConfig config;
    private Connection observer;
    private PlayerBackpack backpack;
    private ItemStack original;
    private final List<Gate> gates = new ArrayList<>();
    private final List<TestController> controllers = new ArrayList<>();
    private final List<FaultAdapter> adapters = new ArrayList<>();

    enum CallerMutation {
        COMPLETE,
        FAIL,
        CANCEL,
        OBTRUDE_VALUE,
        OBTRUDE_EXCEPTION;

        void apply(CompletableFuture<Void> future) {
            var failure = new IllegalStateException("Caller-only completion, not a database outcome");
            switch (this) {
                case COMPLETE -> assertTrue(future.complete(null));
                case FAIL -> assertTrue(future.completeExceptionally(failure));
                case CANCEL -> assertTrue(future.cancel(true));
                case OBTRUDE_VALUE -> future.obtrudeValue(null);
                case OBTRUDE_EXCEPTION -> future.obtrudeException(failure);
            }
        }
    }

    enum FailurePoint {
        BEFORE_DELETE,
        AFTER_WRITE
    }

    @BeforeEach
    void setUp() throws Exception {
        server = MockBukkit.mock();
        server.addSimpleWorld("old_world");
        fixture = new InventoryReadTestPlugin(server);
        config = new SqliteConfig(directory.resolve("backpack-writes.db").toString(), 3);
        openStorage();
        original = StoredInventoryReaderTest.item();
        original.setAmount(23);
        var meta = original.getItemMeta();
        meta.getPersistentDataContainer().set(
                new NamespacedKey("oldaddon", "opaque_state"), PersistentDataType.STRING, "existing-not-a-template");
        original.setItemMeta(meta);
        backpack = seedBackpack();
    }

    @AfterEach
    void tearDown() throws Exception {
        gates.forEach(Gate::release);
        try {
            for (TestController current : controllers) {
                current.closeFixture();
            }
        } finally {
            try {
                if (observer != null) {
                    observer.close();
                }
                for (FaultAdapter current : adapters) {
                    current.shutdown();
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
    }

    @Test
    void unchangedSaveAndAnExplicitMoveSurviveAdapterAndControllerReopen() throws Exception {
        Map<Integer, byte[]> before = storedBytes(backpack);
        complete(controller.saveBackpackInventoryAsync(backpack));
        assertTrue(adapter.attempts.isEmpty());
        assertSameBytes(before, storedBytes(backpack));

        backpack.getInventory().setItem(1, backpack.getInventory().getItem(8));
        backpack.getInventory().setItem(8, null);
        complete(controller.saveBackpackInventoryAsync(backpack));
        assertEquals(2, adapter.attempts.size());
        assertStored(backpack, Map.of(0, original, 1, original));
        assertEquals(0, controller.getUncertainBackpackBaselineCount());
        int writes = adapter.attempts.size();
        complete(controller.saveBackpackInventoryAsync(backpack));
        assertEquals(writes, adapter.attempts.size());

        PlayerBackpack reopened = reopenBackpack(backpack);
        assertItem(original, reopened.getInventory().getItem(0));
        assertItem(original, reopened.getInventory().getItem(1));
        assertNull(reopened.getInventory().getItem(8));
        assertTrue(reopened.getSnapshot().getChangedSlots(reopened.getInventory().getContents()).isEmpty());
    }

    @Test
    void stagedBytesAndAcknowledgementDoNotFollowLaterLiveEdits() throws Exception {
        Map<Integer, byte[]> before = storedBytes(backpack);
        Gate gate = blockFirstWrite(backpack);
        backpack.getInventory().setItem(0, item(7));
        CompletableFuture<Void> first = controller.saveBackpackInventoryAsync(backpack);
        gate.awaitEntered();
        assertFalse(first.isDone());
        assertEquals(1, controller.getPendingBackpackSaveChainCount());
        assertTrue(backpack.getSnapshot().getChangedSlots(backpack.getInventory().getContents()).contains(0));
        assertSameBytes(before, storedBytes(backpack));

        backpack.getInventory().setItem(0, item(11));
        gate.release();
        complete(first);
        assertStored(backpack, Map.of(0, item(7), 8, original));
        assertTrue(backpack.getSnapshot().getChangedSlots(backpack.getInventory().getContents()).contains(0));
        complete(controller.saveBackpackInventoryAsync(backpack));
        assertStored(backpack, Map.of(0, item(11), 8, original));
    }

    @ParameterizedTest
    @EnumSource(CallerMutation.class)
    void callerCannotCompleteOrCancelTheInternalSaveChain(CallerMutation mutation) throws Exception {
        Gate gate = blockFirstWrite(backpack);
        backpack.getInventory().setItem(0, item(7));
        CompletableFuture<Void> view = controller.saveBackpackInventoryAsync(backpack);
        gate.awaitEntered();
        mutation.apply(view);
        assertTrue(view.isDone(), "The caller may change its own observation");
        assertEquals(1, controller.getPendingBackpackSaveChainCount(), "The real database chain must remain held");
        assertTrue(backpack.getSnapshot().getChangedSlots(backpack.getInventory().getContents()).contains(0));

        backpack.getInventory().setItem(0, item(11));
        CompletableFuture<Void> second = controller.saveBackpackInventoryAsync(backpack);
        assertFalse(second.isDone(), "A second staged save must wait for the real first write");
        assertEquals(1, controller.getPendingBackpackSaveChainCount());
        assertEquals(1, adapter.attempts.size());
        gate.release();
        complete(second);
        assertStored(backpack, Map.of(0, item(11), 8, original));
        assertEquals(2, adapter.attempts.size());
        assertEquals(0, controller.getUncertainBackpackBaselineCount());
    }

    @ParameterizedTest
    @EnumSource(FailurePoint.class)
    void partialFailureForcesAllSlotsToRetryWithoutTouchingAnotherBackpack(FailurePoint point) throws Exception {
        PlayerBackpack healthy = seedBackpack();
        Map<Integer, byte[]> healthyBefore = storedBytes(healthy);
        AtomicBoolean failOnce = new AtomicBoolean(true);
        Consumer<Operation> fault = operation -> {
            boolean target = operation.backpackId().equals(backpack.getUniqueId().toString())
                    && (point == FailurePoint.BEFORE_DELETE ? operation.delete() && operation.slot() == 8
                            : !operation.delete() && operation.slot() == 0);
            if (target && failOnce.compareAndSet(true, false)) {
                throw new IllegalStateException("Injected " + point);
            }
        };
        if (point == FailurePoint.BEFORE_DELETE) {
            adapter.before = fault;
        } else {
            adapter.after = fault;
        }
        backpack.getInventory().setItem(0, item(7));
        backpack.getInventory().setItem(8, null);
        CompletableFuture<Void> failed = controller.saveBackpackInventoryAsync(backpack);
        assertThrows(ExecutionException.class, () -> failed.get(WAIT_SECONDS, TimeUnit.SECONDS));
        awaitIdle();
        assertFalse(failOnce.get());
        assertEquals(1, controller.getUncertainBackpackBaselineCount());
        assertTrue(backpack.getSnapshot().getChangedSlots(backpack.getInventory().getContents()).contains(0));
        assertStored(backpack, point == FailurePoint.BEFORE_DELETE
                ? Map.of(0, item(7), 8, original) : Map.of(0, item(7)));
        assertSameBytes(healthyBefore, storedBytes(healthy));

        // A different backing UUID still saves while the first baseline is uncertain.
        healthy.getInventory().setItem(0, item(5));
        complete(controller.saveBackpackInventoryAsync(healthy));
        assertEquals(1, controller.getUncertainBackpackBaselineCount());
        Map<Integer, byte[]> healthySaved = storedBytes(healthy);

        // Fixture-only stale high slot models data left outside the current inventory size.
        seedSlot(backpack.getUniqueId(), 53, item(3));
        adapter.before = operation -> {};
        adapter.after = operation -> {};
        adapter.attempts.clear();
        backpack.getInventory().setItem(0, item(11));
        complete(controller.saveBackpackInventoryAsync(backpack));
        assertEquals(54, adapter.attempts.size());
        assertEquals(IntStream.range(0, 54).boxed().collect(Collectors.toSet()),
                adapter.attempts.stream().map(Operation::slot).collect(Collectors.toSet()));
        assertTrue(adapter.attempts.stream().allMatch(operation ->
                operation.backpackId().equals(backpack.getUniqueId().toString())));
        assertEquals(1, adapter.attempts.stream().filter(operation -> !operation.delete()).count());
        assertStored(backpack, Map.of(0, item(11)));
        assertSameBytes(healthySaved, storedBytes(healthy));
        assertEquals(0, controller.getUncertainBackpackBaselineCount());
        complete(controller.saveBackpackInventoryAsync(backpack));
        assertEquals(54, adapter.attempts.size(), "An unchanged retry must not write a second full inventory");
        controller.shutdown();
        assertFalse(controller.wasLastShutdownClean(), "A recovered write failure remains visible in shutdown accounting");
        PlayerBackpack reopened = reopenBackpack(backpack);
        assertItem(item(11), reopened.getInventory().getItem(0));
        assertNull(reopened.getInventory().getItem(8));
    }

    @Test
    void queuedNewerStateRepairsAWriteThatCommittedThenReportedFailure() throws Exception {
        Gate gate = blockFirstWrite(backpack);
        AtomicBoolean failOnce = new AtomicBoolean(true);
        adapter.after = operation -> {
            if (!operation.delete() && operation.slot() == 0 && failOnce.compareAndSet(true, false)) {
                throw new IllegalStateException("Injected lost acknowledgement after SQLite write");
            }
        };
        backpack.getInventory().setItem(0, item(7));
        CompletableFuture<Void> first = controller.saveBackpackInventoryAsync(backpack);
        gate.awaitEntered();
        backpack.getInventory().setItem(0, item(11));
        CompletableFuture<Void> second = controller.saveBackpackInventoryAsync(backpack);
        assertFalse(second.isDone());
        gate.release();
        assertThrows(ExecutionException.class, () -> first.get(WAIT_SECONDS, TimeUnit.SECONDS));
        complete(second);
        assertEquals(55, adapter.attempts.size(), "One failed write is followed by one 54-slot recovery stage");
        assertStored(backpack, Map.of(0, item(11), 8, original));
        assertEquals(0, controller.getUncertainBackpackBaselineCount());
    }

    @Test
    void shutdownDrainsBothStagedSavesBeforeAFreshControllerLoadsTheDatabase() throws Exception {
        Gate gate = blockFirstWrite(backpack);
        backpack.getInventory().setItem(0, item(7));
        CompletableFuture<Void> first = controller.saveBackpackInventoryAsync(backpack);
        gate.awaitEntered();
        backpack.getInventory().setItem(0, item(11));
        CompletableFuture<Void> second = controller.saveBackpackInventoryAsync(backpack);
        var started = new CountDownLatch(1);
        var shutdownExecutor = Executors.newSingleThreadExecutor();
        try {
            var stopped = shutdownExecutor.submit(() -> {
                started.countDown();
                controller.shutdown();
            });
            assertTrue(started.await(WAIT_SECONDS, TimeUnit.SECONDS));
            assertFalse(stopped.isDone());
            gate.release();
            stopped.get(20, TimeUnit.SECONDS);
            first.get(WAIT_SECONDS, TimeUnit.SECONDS);
            second.get(WAIT_SECONDS, TimeUnit.SECONDS);
            assertTrue(controller.isDestroyed());
            assertTrue(controller.wasLastShutdownClean());
            assertStored(backpack, Map.of(0, item(11), 8, original));
        } finally {
            gate.release();
            shutdownExecutor.shutdownNow();
            assertTrue(shutdownExecutor.awaitTermination(WAIT_SECONDS, TimeUnit.SECONDS));
        }
        PlayerBackpack reopened = reopenBackpack(backpack);
        assertItem(item(11), reopened.getInventory().getItem(0));
        assertItem(original, reopened.getInventory().getItem(8));
    }

    private void openStorage() throws Exception {
        adapter = new FaultAdapter();
        adapters.add(adapter);
        adapter.prepare(config);
        adapter.initStorage(DataType.PLAYER_PROFILE);
        controller = new TestController(adapter);
        controllers.add(controller);
        observer = DriverManager.getConnection(config.jdbcUrl());
    }

    private PlayerBackpack seedBackpack() {
        var owner = server.addPlayer();
        UUID id = UUID.randomUUID();
        var profileKey = new RecordKey(DataScope.PLAYER_PROFILE);
        profileKey.addCondition(FieldKey.PLAYER_UUID, owner.getUniqueId().toString());
        var profile = new RecordSet();
        profile.put(FieldKey.PLAYER_UUID, owner.getUniqueId().toString());
        profile.put(FieldKey.PLAYER_NAME, owner.getName());
        profile.put(FieldKey.PLAYER_BACKPACK_NUM, "1");
        adapter.seed(profileKey, profile);
        var packKey = new RecordKey(DataScope.BACKPACK_PROFILE);
        packKey.addCondition(FieldKey.BACKPACK_ID, id.toString());
        var pack = new RecordSet();
        pack.put(FieldKey.BACKPACK_ID, id.toString());
        pack.put(FieldKey.PLAYER_UUID, owner.getUniqueId().toString());
        pack.put(FieldKey.BACKPACK_NUMBER, "1");
        pack.put(FieldKey.BACKPACK_SIZE, "9");
        pack.put(FieldKey.BACKPACK_NAME, DataUtils.profileDataBase64("Existing backpack"));
        adapter.seed(packKey, pack);
        seedSlot(id, 0, original);
        seedSlot(id, 8, original);
        PlayerBackpack loaded = controller.getBackpack(id.toString());
        assertNotNull(loaded);
        return loaded;
    }

    private void seedSlot(UUID id, int slot, ItemStack item) {
        var key = new RecordKey(DataScope.BACKPACK_INVENTORY);
        key.addCondition(FieldKey.BACKPACK_ID, id.toString());
        key.addCondition(FieldKey.INVENTORY_SLOT, Integer.toString(slot));
        var data = new RecordSet();
        data.put(FieldKey.BACKPACK_ID, id.toString());
        data.put(FieldKey.INVENTORY_SLOT, Integer.toString(slot));
        data.put(FieldKey.INVENTORY_ITEM, item);
        adapter.seed(key, data);
    }

    private PlayerBackpack reopenBackpack(PlayerBackpack previous) throws Exception {
        if (!controller.isDestroyed()) {
            controller.shutdown();
        }
        observer.close();
        adapter.shutdown();
        adapters.remove(adapter);
        openStorage();
        PlayerBackpack loaded = controller.getBackpack(previous.getUniqueId().toString());
        assertNotNull(loaded);
        assertEquals(previous.getUniqueId(), loaded.getUniqueId());
        assertEquals(previous.getOwner().getUniqueId(), loaded.getOwner().getUniqueId());
        assertEquals(previous.getId(), loaded.getId());
        assertEquals(previous.getSize(), loaded.getSize());
        assertEquals(previous.getName(), loaded.getName());
        return loaded;
    }

    private ItemStack item(int amount) {
        ItemStack changed = original.clone();
        changed.setAmount(amount);
        return changed;
    }

    private Gate blockFirstWrite(PlayerBackpack target) {
        Gate gate = new Gate();
        gates.add(gate);
        AtomicBoolean first = new AtomicBoolean(true);
        adapter.before = operation -> {
            if (!operation.delete() && operation.slot() == 0
                    && operation.backpackId().equals(target.getUniqueId().toString())
                    && first.compareAndSet(true, false)) {
                gate.block();
            }
        };
        return gate;
    }

    private void complete(CompletableFuture<Void> future) throws Exception {
        future.get(WAIT_SECONDS, TimeUnit.SECONDS);
        awaitIdle();
    }

    private void awaitIdle() {
        awaitCondition(() -> controller.getPendingBackpackSaveChainCount() == 0
                && controller.getPendingWriteTaskCount() == 0);
    }

    private static void awaitCondition(BooleanSupplier condition) {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(WAIT_SECONDS);
        while (!condition.getAsBoolean() && System.nanoTime() < deadline && !Thread.currentThread().isInterrupted()) {
            LockSupport.parkNanos(TimeUnit.MILLISECONDS.toNanos(1));
        }
        assertTrue(condition.getAsBoolean(), "The observed asynchronous state did not settle before the deadline");
    }

    private Map<Integer, byte[]> storedBytes(PlayerBackpack target) throws Exception {
        var result = new HashMap<Integer, byte[]>();
        String sql = "SELECT " + FIELD_INVENTORY_SLOT + "," + FIELD_INVENTORY_ITEM
                + " FROM " + SqlUtils.mapTable(DataScope.BACKPACK_INVENTORY)
                + " WHERE " + FIELD_BACKPACK_ID + "=? ORDER BY " + FIELD_INVENTORY_SLOT;
        try (var statement = observer.prepareStatement(sql)) {
            statement.setString(1, target.getUniqueId().toString());
            try (var rows = statement.executeQuery()) {
                while (rows.next()) {
                    result.put(rows.getInt(1), rows.getBytes(2));
                }
            }
        }
        return result;
    }

    private void assertStored(PlayerBackpack target, Map<Integer, ItemStack> expected) throws Exception {
        Map<Integer, byte[]> actual = storedBytes(target);
        assertEquals(expected.keySet(), actual.keySet());
        expected.forEach((slot, item) -> assertItem(item,
                StoredInventoryReaderTest.row(Integer.toString(slot), actual.get(slot))
                        .getItemStack(FieldKey.INVENTORY_ITEM)));
    }

    private static void assertSameBytes(Map<Integer, byte[]> expected, Map<Integer, byte[]> actual) {
        assertEquals(expected.keySet(), actual.keySet());
        expected.forEach((slot, bytes) -> assertArrayEquals(bytes, actual.get(slot)));
    }

    private static void assertItem(ItemStack expected, ItemStack actual) {
        assertNotNull(actual);
        assertEquals(expected.getType(), actual.getType());
        assertEquals(expected.getAmount(), actual.getAmount());
        assertEquals(expected.getItemMeta(), actual.getItemMeta());
    }

    private static Field field(Class<?> type, String name) throws Exception {
        Field found = type.getDeclaredField(name);
        found.setAccessible(true);
        return found;
    }

    private record Operation(String backpackId, int slot, boolean delete) {}

    private static Operation operation(RecordKey key, boolean delete) {
        assertEquals(DataScope.BACKPACK_INVENTORY, key.getScope());
        Map<FieldKey, String> conditions = key.getConditions().stream().collect(Collectors.toMap(
                condition -> condition.getFirstValue(), condition -> condition.getSecondValue()));
        assertEquals(2, conditions.size());
        return new Operation(conditions.get(FieldKey.BACKPACK_ID),
                Integer.parseInt(conditions.get(FieldKey.INVENTORY_SLOT)), delete);
    }

    private static final class FaultAdapter extends SqliteAdapter {
        private final List<Operation> attempts = new CopyOnWriteArrayList<>();
        private volatile Consumer<Operation> before = operation -> {};
        private volatile Consumer<Operation> after = operation -> {};

        private void seed(RecordKey key, RecordSet data) {
            super.setData(key, data);
        }

        @Override
        public void setData(RecordKey key, RecordSet data) {
            Operation operation = operation(key, false);
            attempts.add(operation);
            before.accept(operation);
            super.setData(key, data);
            after.accept(operation);
        }

        @Override
        public void deleteData(RecordKey key) {
            Operation operation = operation(key, true);
            attempts.add(operation);
            before.accept(operation);
            super.deleteData(key);
            after.accept(operation);
        }
    }

    private static final class TestController extends ProfileDataController {
        private TestController(SqliteAdapter adapter) throws Exception {
            field(ADataController.class, "dataAdapter").set(this, adapter);
            readExecutor = Executors.newSingleThreadExecutor();
            writeExecutor = Executors.newFixedThreadPool(2);
            callbackExecutor = Executors.newSingleThreadExecutor();
        }

        private void closeFixture() throws Exception {
            readExecutor.shutdownNow();
            callbackExecutor.shutdownNow();
            writeExecutor.shutdown();
            try {
                if (!writeExecutor.awaitTermination(WAIT_SECONDS, TimeUnit.SECONDS)) {
                    writeExecutor.shutdownNow();
                    assertTrue(writeExecutor.awaitTermination(WAIT_SECONDS, TimeUnit.SECONDS));
                }
            } finally {
                ((BackpackCache) field(ProfileDataController.class, "backpackCache").get(this)).clean();
            }
        }
    }

    private static final class Gate {
        private final CountDownLatch entered = new CountDownLatch(1);
        private final CountDownLatch released = new CountDownLatch(1);

        private void block() {
            entered.countDown();
            try {
                if (!released.await(WAIT_SECONDS, TimeUnit.SECONDS)) {
                    throw new AssertionError("The fixture did not release its database writer");
                }
            } catch (InterruptedException failure) {
                Thread.currentThread().interrupt();
                throw new AssertionError("Database writer fixture was interrupted", failure);
            }
        }

        private void awaitEntered() throws InterruptedException {
            assertTrue(entered.await(WAIT_SECONDS, TimeUnit.SECONDS));
        }

        private void release() {
            released.countDown();
        }
    }
}
