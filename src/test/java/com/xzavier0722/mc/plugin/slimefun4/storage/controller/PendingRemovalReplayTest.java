package com.xzavier0722.mc.plugin.slimefun4.storage.controller;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;

/** Real container mutations and controlled interleavings with recorded persistence submissions; not a database fixture. */
class PendingRemovalReplayTest {
    @Test
    void cancellationSubmitsDeletionEvenWhenTheCacheIsAlreadyEmpty() {
        var data = seeded();
        data.setPendingRemove(true);
        data.removeData("recipe");
        assertNull(data.getData("recipe"));
        assertTrue(data.updates.isEmpty());
        assertEquals("old-recipe", data.submitted.get("recipe"));

        data.setPendingRemove(false);

        assertEquals(List.of("recipe"), data.updates, "Cancellation must submit the pending deletion");
        assertFalse(data.submitted.containsKey("recipe"));
        assertEquals(data.getAllData(), data.submitted);
        assertFalse(data.isPendingRemove());
    }

    @Test
    void pendingWritesStillCoalesceToTheLastValue() {
        var data = seeded();
        data.setPendingRemove(true);
        data.setData("recipe", "first");
        data.setData("recipe", "last");
        assertTrue(data.updates.isEmpty());
        data.setPendingRemove(false);
        assertEquals(List.of("recipe"), data.updates);
        assertEquals("last", data.submitted.get("recipe"));
    }

    @Test
    void writeThenDeleteDoesNotForgetTheFinalDeletion() {
        var data = seeded();
        data.setPendingRemove(true);
        data.setData("recipe", "temporary");
        data.removeData("recipe");
        data.setPendingRemove(false);
        assertEquals(List.of("recipe"), data.updates);
        assertFalse(data.submitted.containsKey("recipe"));
    }

    @Test
    void deleteThenWritePreservesTheFinalReplacement() {
        var data = seeded();
        data.setPendingRemove(true);
        data.removeData("recipe");
        data.setData("recipe", "replacement");
        data.setPendingRemove(false);
        assertEquals(List.of("recipe"), data.updates);
        assertEquals("replacement", data.submitted.get("recipe"));
    }

    @Test
    void repeatedDeletionIsSubmittedOnlyOnce() {
        var data = seeded();
        data.setPendingRemove(true);
        data.removeData("recipe");
        data.removeData("recipe");
        data.removeData("recipe");
        data.setPendingRemove(false);
        assertEquals(List.of("recipe"), data.updates);
    }

    @Test
    void repeatedCancellationDoesNotReplayAnOldRemoval() {
        var data = seeded();
        data.setPendingRemove(true);
        data.removeData("recipe");
        data.setPendingRemove(false);
        assertEquals(List.of("recipe"), data.updates);
        data.setData("recipe", "new-active-value");
        data.updates.clear();
        data.setPendingRemove(false);
        data.setPendingRemove(true);
        data.setPendingRemove(false);
        assertTrue(data.updates.isEmpty());
        assertEquals("new-active-value", data.submitted.get("recipe"));
    }

    @Test
    void completedRemovalNeverSubmitsCapturedChanges() {
        var data = seeded();
        data.setPendingRemove(true);
        data.removeData("recipe");
        data.setData("temporary", "not-persisted");
        data.setPendingRemove(true);
        assertTrue(data.updates.isEmpty());
        assertEquals(Map.of("recipe", "old-recipe", "owner", "owner-uuid"), data.submitted);
    }

    @Test
    void missingLoadedKeyKeepsTheExistingNoOpBehavior() {
        var data = seeded();
        data.setPendingRemove(true);
        data.removeData("absent");
        data.setPendingRemove(false);
        assertTrue(data.updates.isEmpty());
        assertEquals(data.getAllData(), data.submitted);
    }

    @Test
    void deletionRecordedBeforeLoadIsNotUndoneByLoadedData() {
        var data = new RecordingContainer("world;10:64:-20", "OLD_MACHINE");
        data.setIsDataLoaded(false);
        data.setPendingRemove(true);
        data.removeData("recipe");
        // Reproduce a completed load filling the cache after the deletion was captured.
        data.setCacheInternal("recipe", "old-recipe", false);
        data.submitted.put("recipe", "old-recipe");
        data.setIsDataLoaded(true);
        data.setPendingRemove(false);
        assertNull(data.getData("recipe"));
        assertEquals(List.of("recipe"), data.updates);
        assertFalse(data.submitted.containsKey("recipe"));
    }

    @Test
    void emptyAndOpaqueStringsAreNotDeletionMarkers() {
        var data = seeded();
        String payload = "  {\"id\":\"UNREGISTERED_OLD_ID\",\"count\":\"9007199254740993\"}\n";
        data.setPendingRemove(true);
        data.setData("empty", "");
        data.setData("payload", payload);
        data.removeData("recipe");
        data.setPendingRemove(false);
        assertEquals("", data.submitted.get("empty"));
        assertEquals(payload, data.submitted.get("payload"));
        assertEquals("owner-uuid", data.submitted.get("owner"));
        assertEquals("OLD_MACHINE", data.getSfId());
        assertEquals("world;10:64:-20", data.getKey());
        assertEquals(Set.of("empty", "payload", "recipe"), new HashSet<>(data.updates));
    }

    @Test
    void sameLocationDoesNotMixDifferentContainerInstances() {
        var first = seeded();
        var second = seeded();
        first.setPendingRemove(true);
        second.setPendingRemove(true);
        first.removeData("recipe");
        second.setData("recipe", "other-container");
        first.setPendingRemove(false);
        assertFalse(first.submitted.containsKey("recipe"));
        assertTrue(second.updates.isEmpty());
        second.setPendingRemove(false);
        assertEquals("other-container", second.submitted.get("recipe"));
        assertFalse(first.submitted.containsKey("recipe"));
    }

    @Test
    void activeMutationsKeepTheirExistingSchedulingBehavior() {
        var data = seeded();
        data.removeData("recipe");
        data.removeData("recipe");
        data.setData("recipe", "active");
        assertEquals(List.of("recipe", "recipe"), data.updates);
        assertEquals("active", data.submitted.get("recipe"));
    }

    @Test
    void newThenDeletedKeyDoesNotLeaveAPendingWrite() {
        var data = seeded();
        data.setPendingRemove(true);
        data.setData("new", "temporary");
        data.removeData("new");
        data.setPendingRemove(false);
        assertFalse(data.submitted.containsKey("new"));
        assertEquals(data.getAllData(), data.submitted);
        assertEquals(List.of("new"), data.updates);
    }

    @Test
    void randomizedSequentialChangesMatchTheFinalCacheAfterCancellation() {
        var random = new Random(20261001L);
        for (int sample = 0; sample < 1000; sample++) {
            var data = seeded();
            data.setPendingRemove(true);
            var touched = new HashSet<String>();
            for (int step = 0; step < 80; step++) {
                String key = "field-" + random.nextInt(8);
                if (random.nextBoolean()) {
                    data.setData(key, "opaque-value-" + random.nextLong());
                    touched.add(key);
                } else {
                    if (data.getData(key) != null) touched.add(key);
                    data.removeData(key);
                }
            }
            assertTrue(data.updates.isEmpty());
            data.setPendingRemove(false);
            assertEquals(data.getAllData(), data.submitted, "sample " + sample);
            assertEquals(touched, new HashSet<>(data.updates));
            assertEquals(touched.size(), data.updates.size());
        }
    }

    @Test
    void cancellationCannotLoseAWriteBetweenThePendingDecisionAndCapture() throws InterruptedException {
        var data = interleavedSeed();
        data.setPendingRemove(true);

        runInterleaved(
                data,
                PausePoint.CAPTURE,
                () -> data.setData("recipe", "replacement"),
                () -> data.setPendingRemove(false));

        assertEquals("replacement", data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);
        assertEquals(List.of("recipe"), data.updates);
        assertFalse(data.isPendingRemove());
    }

    @Test
    void cancellationCannotLoseADeletionBetweenThePendingDecisionAndCapture() throws InterruptedException {
        var data = interleavedSeed();
        data.setPendingRemove(true);

        runInterleaved(
                data, PausePoint.CAPTURE, () -> data.removeData("recipe"), () -> data.setPendingRemove(false));

        assertNull(data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);
        assertEquals(List.of("recipe"), data.updates);
        assertFalse(data.isPendingRemove());
    }

    @Test
    void cancellationReplayCannotOverwriteANewerActiveWrite() throws InterruptedException {
        var data = interleavedSeed();
        data.setPendingRemove(true);
        data.setData("recipe", "pending-replacement");

        runInterleaved(
                data,
                PausePoint.REPLAY_WRITE,
                () -> data.setPendingRemove(false),
                () -> data.setData("recipe", "new-active-value"));

        assertEquals("new-active-value", data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);
        assertEquals(List.of("recipe", "recipe"), data.updates);
    }

    @Test
    void cancellationReplayCannotResurrectANewerActiveDeletion() throws InterruptedException {
        var data = interleavedSeed();
        data.setPendingRemove(true);
        data.setData("recipe", "pending-replacement");

        runInterleaved(
                data, PausePoint.REPLAY_WRITE, () -> data.setPendingRemove(false), () -> data.removeData("recipe"));

        assertNull(data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);
        assertEquals(List.of("recipe", "recipe"), data.updates);
    }

    @Test
    void cancellationDeletionReplayCannotEraseANewerActiveWrite() throws InterruptedException {
        var data = interleavedSeed();
        data.setPendingRemove(true);
        data.removeData("recipe");

        runInterleaved(
                data,
                PausePoint.REPLAY_DELETE,
                () -> data.setPendingRemove(false),
                () -> data.setData("recipe", "new-active-value"));

        assertEquals("new-active-value", data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);
        assertEquals(List.of("recipe", "recipe"), data.updates);
    }

    @Test
    void anotherContainerCanFinishItsChangesWhileCancellationReplayIsPaused() throws InterruptedException {
        var data = interleavedSeed();
        data.setPendingRemove(true);
        data.setData("recipe", "pending-replacement");
        var independent = seeded();
        independent.setPendingRemove(true);
        var paused = new ConcurrentCall("paused-storage-operation", () -> data.setPendingRemove(false));
        var other = new ConcurrentCall("independent-storage-operation", () -> {
            independent.setData("recipe", "independent-replacement");
            independent.setPendingRemove(false);
        });
        data.pausePoint = PausePoint.REPLAY_WRITE;
        data.pausedThread = paused.thread;
        try {
            paused.thread.start();
            assertTrue(data.entered.await(5, TimeUnit.SECONDS), "Cancellation replay was not reached");
            other.thread.start();
            other.awaitFinished();
            assertEquals("independent-replacement", independent.getData("recipe"));
            assertEquals(independent.getAllData(), independent.submitted);
            assertEquals(List.of("recipe"), independent.updates);
        } finally {
            data.release.countDown();
            assertAll(paused::awaitFinished, other::awaitFinished);
        }
        assertEquals("pending-replacement", data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);
    }

    @Test
    void protectedCaptureKeepsDeferredValuesDeletionsAndActiveNoOpBehavior() {
        var data = seeded();
        data.setWhilePendingRemove("recipe", "ignored-while-active");
        assertEquals("old-recipe", data.getData("recipe"));
        assertTrue(data.updates.isEmpty());

        data.setPendingRemove(true);
        data.setWhilePendingRemove("recipe", "captured-only");
        assertEquals("old-recipe", data.getData("recipe"), "Direct capture does not mutate the live cache");
        assertTrue(data.updates.isEmpty());
        data.setPendingRemove(false);
        assertEquals("captured-only", data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);

        data.setPendingRemove(true);
        data.setWhilePendingRemove("recipe", null);
        assertEquals("captured-only", data.getData("recipe"));
        data.setPendingRemove(false);
        assertNull(data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);
        assertEquals(List.of("recipe", "recipe"), data.updates);
    }

    @Test
    void synchronizedAddonOverrideSharesTheCancellationMonitor() throws InterruptedException {
        var data = new SynchronizedOverrideContainer();
        data.setData("recipe", "old-recipe");
        data.setPendingRemove(true);
        data.setData("recipe", "pending-replacement");
        data.updates.clear();

        // The writer owns the subclass's intrinsic monitor before cancellation starts. A
        // separate internal mutation lock would deadlock when replay calls that same override.
        runInterleaved(
                data,
                PausePoint.REPLAY_WRITE,
                () -> data.setData("recipe", "new-active-value"),
                () -> data.setPendingRemove(false));

        assertEquals("new-active-value", data.getData("recipe"));
        assertEquals(data.getAllData(), data.submitted);
        assertEquals(List.of("recipe"), data.updates);
        assertFalse(data.isPendingRemove());
    }

    private static InterleavingContainer interleavedSeed() {
        var data = new InterleavingContainer();
        data.setData("recipe", "old-recipe");
        data.setData("owner", "owner-uuid");
        data.updates.clear();
        return data;
    }

    private static void runInterleaved(
            InterleavingContainer data, PausePoint point, Runnable pausedOperation, Runnable competingOperation)
            throws InterruptedException {
        var paused = new ConcurrentCall("paused-storage-operation", pausedOperation);
        var competing = new ConcurrentCall("competing-storage-operation", competingOperation);
        data.pausePoint = point;
        data.pausedThread = paused.thread;
        try {
            paused.thread.start();
            assertTrue(data.entered.await(5, TimeUnit.SECONDS), "The selected storage boundary was not reached");
            competing.thread.start();
            assertTrue(competing.started.await(5, TimeUnit.SECONDS), "The competing operation did not start");
            awaitBlockedOrCompleted(competing.thread);
        } finally {
            data.release.countDown();
            assertAll(paused::awaitFinished, competing::awaitFinished);
        }
    }

    private static void awaitBlockedOrCompleted(Thread thread) {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        // Let the competing call either reach the held mutation boundary or finish. No timed
        // race or favorable scheduling is needed: the paused call cannot proceed until release.
        while (thread.isAlive() && thread.getState() != Thread.State.BLOCKED) {
            assertTrue(System.nanoTime() < deadline, "The competing operation neither blocked nor completed");
            Thread.yield();
        }
    }

    private enum PausePoint {
        CAPTURE,
        REPLAY_WRITE,
        REPLAY_DELETE
    }

    private static final class ConcurrentCall {
        private final CountDownLatch started = new CountDownLatch(1);
        private final AtomicReference<Throwable> failure = new AtomicReference<>();
        private final Thread thread;

        ConcurrentCall(String name, Runnable operation) {
            thread = new Thread(() -> {
                started.countDown();
                try {
                    operation.run();
                } catch (Throwable thrown) {
                    failure.set(thrown);
                }
            }, name);
            thread.setDaemon(true);
        }

        void awaitFinished() throws InterruptedException {
            thread.join(TimeUnit.SECONDS.toMillis(5));
            assertFalse(thread.isAlive(), "A storage operation did not finish");
            assertNull(failure.get(), () -> "Storage operation failed: " + failure.get());
        }
    }

    private static class InterleavingContainer extends RecordingContainer {
        private final CountDownLatch entered = new CountDownLatch(1);
        private final CountDownLatch release = new CountDownLatch(1);
        private volatile Thread pausedThread;
        private volatile PausePoint pausePoint;

        InterleavingContainer() {
            super("world;10:64:-20", "OLD_MACHINE");
        }

        @Override
        protected void setWhilePendingRemove(String key, String value) {
            pauseAt(PausePoint.CAPTURE);
            super.setWhilePendingRemove(key, value);
        }

        @Override
        public void setData(String key, String value) {
            pauseAt(PausePoint.REPLAY_WRITE);
            super.setData(key, value);
        }

        @Override
        protected String removeCacheInternal(String key) {
            pauseAt(PausePoint.REPLAY_DELETE);
            return super.removeCacheInternal(key);
        }

        private void pauseAt(PausePoint point) {
            if (Thread.currentThread() != pausedThread || point != pausePoint) {
                return;
            }
            entered.countDown();
            try {
                assertTrue(release.await(5, TimeUnit.SECONDS), "The paused storage operation was not released");
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw new AssertionError(interrupted);
            }
        }
    }

    private static final class SynchronizedOverrideContainer extends InterleavingContainer {
        @Override
        public synchronized void setData(String key, String value) {
            super.setData(key, value);
        }
    }

    private static RecordingContainer seeded() {
        var data = new RecordingContainer("world;10:64:-20", "OLD_MACHINE");
        data.setData("recipe", "old-recipe");
        data.setData("owner", "owner-uuid");
        data.updates.clear();
        return data;
    }

    private static class RecordingContainer extends ASlimefunDataContainer {
        final List<String> updates = Collections.synchronizedList(new ArrayList<>());
        final Map<String, String> submitted = new ConcurrentHashMap<>();

        RecordingContainer(String key, String itemId) {
            super(key, itemId);
            setIsDataLoaded(true);
        }

        @Override
        public void scheduleUpdateData(String key) {
            updates.add(key);
            String value = getCacheInternal(key);
            if (value == null) submitted.remove(key);
            else submitted.put(key, value);
        }
    }
}
