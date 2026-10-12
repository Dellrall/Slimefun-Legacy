package io.github.thebusybiscuit.slimefun4.implementation.tasks;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import io.github.thebusybiscuit.slimefun4.core.services.scheduling.SlimefunScheduler;
import io.github.thebusybiscuit.slimefun4.core.services.scheduling.TaskHandle;
import io.github.thebusybiscuit.slimefun4.implementation.Slimefun;
import java.lang.reflect.Field;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import java.util.function.IntConsumer;
import org.bukkit.Location;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockbukkit.mockbukkit.MockBukkit;

/**
 * Exercises the real coordinator and profiler with controlled region dispatch. Region ownership is deliberately
 * denied at the callback boundary so these accounting tests never read world blocks or machine storage.
 */
class TestTickerTaskFoliaDispatch {

    private final List<Runnable> callbacks = new ArrayList<>();
    private final AtomicInteger ownershipChecks = new AtomicInteger();
    private InventoryReadTestPlugin fixture;
    private TickerTask task;
    private AtomicBoolean running;
    private Function<Runnable, TaskHandle> dispatch = callback -> new Handle(false);
    private IntConsumer ownershipCheck = ignored -> {};

    @BeforeEach
    void setUp() throws Exception {
        var server = MockBukkit.mock();
        fixture = new InventoryReadTestPlugin(server);
        var world = server.addSimpleWorld("world");
        task = new TickerTask();
        task.enableTicker(new Location(world, 1, 64, 1));
        task.enableTicker(new Location(world, 33, 64, 1));
        Field runningField = TickerTask.class.getDeclaredField("running");
        runningField.setAccessible(true);
        running = (AtomicBoolean) runningField.get(task);
        SlimefunScheduler scheduler = (SlimefunScheduler) Proxy.newProxyInstance(
                SlimefunScheduler.class.getClassLoader(),
                new Class<?>[] {SlimefunScheduler.class},
                (proxy, method, args) -> switch (method.getName()) {
                    case "isFolia" -> true;
                    case "runAt" -> {
                        Runnable callback = (Runnable) args[1];
                        callbacks.add(callback);
                        yield dispatch.apply(callback);
                    }
                    case "isOwnedByCurrentRegion" -> {
                        ownershipCheck.accept(ownershipChecks.incrementAndGet());
                        yield false;
                    }
                    default -> throw new AssertionError("Unexpected scheduler call: " + method.getName());
                });
        Field schedulerField = Slimefun.class.getDeclaredField("schedulerService");
        schedulerField.setAccessible(true);
        schedulerField.set(Slimefun.instance(), scheduler);
    }

    @AfterEach
    void tearDown() {
        try {
            if (fixture != null) {
                Slimefun.getProfiler().kill();
                fixture.close();
            }
        } finally {
            MockBukkit.unmock();
        }
    }

    @Test
    void acceptedCallbacksKeepCoordinatorAndProfilerActiveUntilEveryChunkCompletes() {
        task.run();

        assertEquals(2, callbacks.size());
        assertCycleActive();
        task.run();
        assertEquals(2, callbacks.size(), "An active cycle must suppress the next coordinator run");
        callbacks.getFirst().run();
        assertCycleActive();
        callbacks.getLast().run();
        assertCycleFinished();
        assertEquals(2, ownershipChecks.get());

        task.run();
        assertEquals(4, callbacks.size(), "A completed cycle must allow the next coordinator run");
        callbacks.get(2).run();
        callbacks.get(3).run();
        assertCycleFinished();
    }

    @Test
    void duplicateCallbackCannotFinishWhileAnotherChunkIsPending() {
        task.run();

        callbacks.getFirst().run();
        callbacks.getFirst().run();

        assertCycleActive();
        assertEquals(1, ownershipChecks.get());
        callbacks.getLast().run();
        assertCycleFinished();
    }

    @Test
    void completedCallbackAndCancelledHandleCountAsOneChunk() {
        dispatch = callback -> {
            if (callbacks.size() == 1) {
                callback.run();
                return new Handle(true);
            }
            return new Handle(false);
        };

        task.run();

        assertCycleActive();
        assertEquals(1, ownershipChecks.get());
        callbacks.getLast().run();
        assertCycleFinished();
    }

    @Test
    void rejectedChunkCannotRunLateOrCompleteAnotherChunksReservation() {
        dispatch = callback -> new Handle(callbacks.size() == 1);

        task.run();
        callbacks.getFirst().run();

        assertCycleActive();
        assertEquals(0, ownershipChecks.get());
        callbacks.getLast().run();
        assertCycleFinished();
        assertEquals(1, ownershipChecks.get());
    }

    @Test
    void allRejectedChunksFinishWithoutExecutingAndDoNotAffectTheNextCycle() {
        dispatch = callback -> new Handle(true);
        task.run();
        assertCycleFinished();

        dispatch = callback -> new Handle(false);
        task.run();
        callbacks.getFirst().run();
        callbacks.get(1).run();

        assertCycleActive();
        assertEquals(0, ownershipChecks.get());
        callbacks.get(2).run();
        callbacks.get(3).run();
        assertCycleFinished();
        assertEquals(2, ownershipChecks.get());
    }

    @ParameterizedTest
    @EnumSource(FailureMode.class)
    void schedulingFailureCompletesOnlyAnUnclaimedChunk(FailureMode mode) {
        dispatch = callback -> {
            if (callbacks.size() == 1) {
                if (mode.completed) callback.run();
                if (mode.linkage) throw new NoClassDefFoundError("Injected scheduler linkage failure");
                throw new IllegalStateException("Injected scheduler failure");
            }
            return new Handle(false);
        };

        task.run();
        callbacks.getFirst().run();

        assertCycleActive();
        assertEquals(mode.completed ? 1 : 0, ownershipChecks.get());
        callbacks.getLast().run();
        assertCycleFinished();
    }

    @Test
    void runningRegionRetainsItsReservationWhenCancellationRacesWithDispatch() throws Exception {
        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch finish = new CountDownLatch(1);
        ExecutorService worker = Executors.newSingleThreadExecutor();
        List<Future<?>> runs = new ArrayList<>();
        ownershipCheck = index -> {
            if (index == 1) {
                started.countDown();
                await(finish);
            }
        };
        dispatch = callback -> {
            if (callbacks.size() == 1) {
                runs.add(worker.submit(callback));
                await(started);
                return new Handle(true);
            }
            return new Handle(false);
        };

        try {
            task.run();
            callbacks.getLast().run();
            assertCycleActive();
            task.run();
            assertEquals(2, callbacks.size(), "No new cycle may start while the first region is still active");
            finish.countDown();
            runs.getFirst().get(5, TimeUnit.SECONDS);
            assertCycleFinished();
            assertEquals(2, ownershipChecks.get());
        } finally {
            finish.countDown();
            worker.shutdownNow();
            assertTrue(worker.awaitTermination(5, TimeUnit.SECONDS));
        }
    }

    @Test
    void emptyCycleFinishesWithoutDispatching() throws Exception {
        task = new TickerTask();
        Field runningField = TickerTask.class.getDeclaredField("running");
        runningField.setAccessible(true);
        running = (AtomicBoolean) runningField.get(task);

        task.run();

        assertTrue(callbacks.isEmpty());
        assertCycleFinished();
    }

    private void assertCycleActive() {
        assertTrue(running.get(), "Pending or running chunks must keep the coordinator active");
        assertTrue(Slimefun.getProfiler().isProfiling(), "The cycle's profiler must stay open until regions finish");
    }

    private void assertCycleFinished() {
        assertFalse(running.get());
        assertFalse(Slimefun.getProfiler().isProfiling());
    }

    private static void await(CountDownLatch latch) {
        try {
            assertTrue(latch.await(5, TimeUnit.SECONDS));
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            throw new AssertionError(failure);
        }
    }

    private enum FailureMode {
        BEFORE_CALLBACK(false, false),
        AFTER_CALLBACK(true, false),
        LINKAGE_BEFORE_CALLBACK(false, true),
        LINKAGE_AFTER_CALLBACK(true, true);

        private final boolean completed;
        private final boolean linkage;

        FailureMode(boolean completed, boolean linkage) {
            this.completed = completed;
            this.linkage = linkage;
        }
    }

    private static final class Handle implements TaskHandle {
        private boolean cancelled;

        private Handle(boolean cancelled) {
            this.cancelled = cancelled;
        }

        @Override
        public void cancel() {
            cancelled = true;
        }

        @Override
        public boolean isCancelled() {
            return cancelled;
        }
    }
}
