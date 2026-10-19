package io.github.thebusybiscuit.slimefun4.implementation.scheduling;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.thebusybiscuit.slimefun4.api.platform.PlatformCompatibilityService;
import io.github.thebusybiscuit.slimefun4.core.services.scheduling.TaskHandle;
import io.papermc.paper.threadedregions.scheduler.EntityScheduler;
import io.papermc.paper.threadedregions.scheduler.ScheduledTask;
import java.lang.reflect.Proxy;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;
import java.util.logging.Logger;
import java.util.stream.Stream;
import org.bukkit.entity.Entity;
import org.bukkit.plugin.IllegalPluginAccessException;
import org.bukkit.plugin.Plugin;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.MethodSource;

/** Exercises native submission failures without conflating them with entity retirement. */
class TestPaperSchedulerSubmissionFailure {

    @ParameterizedTest
    @MethodSource("failedSubmissions")
    void rejectedSubmissionReleasesRegistrationAndPreservesOriginalFailure(Submission submission, Throwable failure) {
        var fixture = new Fixture();
        fixture.failure = failure;
        var work = new AtomicInteger();
        var retired = new AtomicInteger();

        Throwable thrown = assertThrows(
                failure.getClass(), () -> submission.submit(fixture, work::incrementAndGet, retired::incrementAndGet));

        assertSame(failure, thrown, "Callers must receive the original native submission failure");
        assertEquals(1, fixture.submissions);
        assertEquals(0, fixture.scheduler.getActiveTaskCount(), "Rejected work must not remain registered");
        assertTrue(fixture.scheduler.isAcceptingTasks(), "One rejected submission must not close the scheduler");
        assertEquals(0, work.get());
        assertEquals(0, retired.get(), "A submission exception is not an entity-retirement callback");
        assertEquals(0, fixture.cancellations.get(), "No native task was returned to cancel");
    }

    static Stream<Arguments> failedSubmissions() {
        return Stream.of(Submission.values())
                .flatMap(submission -> Stream.of(
                        Arguments.of(
                                submission,
                                new IllegalPluginAccessException("Plugin attempted to register task while disabled")),
                        Arguments.of(submission, new NoClassDefFoundError("Unavailable scheduler implementation"))));
    }

    @ParameterizedTest
    @EnumSource(Submission.class)
    void laterAcceptedWorkKeepsItsExecutionAndCancellationBehavior(Submission submission) {
        var fixture = new Fixture();
        fixture.failure = new IllegalPluginAccessException("Controlled native rejection");
        var work = new AtomicInteger();
        var retired = new AtomicInteger();

        assertThrows(
                IllegalPluginAccessException.class,
                () -> submission.submit(fixture, work::incrementAndGet, retired::incrementAndGet));
        fixture.failure = null;
        TaskHandle accepted = submission.submit(fixture, work::incrementAndGet, retired::incrementAndGet);

        assertEquals(2, fixture.submissions);
        assertEquals(1, fixture.scheduler.getActiveTaskCount(), "Only the accepted task may remain registered");
        assertFalse(accepted.isCancelled());
        fixture.task.accept(fixture.nativeTask);
        assertEquals(1, work.get());
        assertEquals(0, retired.get());
        assertEquals(submission == Submission.REPEATING ? 1 : 0, fixture.scheduler.getActiveTaskCount());

        accepted.cancel();
        accepted.cancel();
        fixture.task.accept(fixture.nativeTask);
        assertTrue(accepted.isCancelled());
        assertEquals(0, fixture.scheduler.getActiveTaskCount());
        assertEquals(1, fixture.cancellations.get());
        assertEquals(1, work.get(), "Cancelling the accepted handle must still suppress later execution");
        assertEquals(0, retired.get());
    }

    @ParameterizedTest
    @EnumSource(Submission.class)
    void quiescedSchedulerStillRejectsWithoutSubmittingOrRetiring(Submission submission) {
        var fixture = new Fixture();
        fixture.failure = new IllegalPluginAccessException("Native submission must not be attempted");
        fixture.scheduler.quiesce();
        var work = new AtomicInteger();
        var retired = new AtomicInteger();

        TaskHandle rejected = submission.submit(fixture, work::incrementAndGet, retired::incrementAndGet);

        assertTrue(rejected.isCancelled());
        assertFalse(fixture.scheduler.isAcceptingTasks());
        assertEquals(0, fixture.scheduler.getActiveTaskCount());
        assertEquals(0, fixture.submissions);
        assertEquals(0, work.get());
        assertEquals(0, retired.get());
    }

    enum Submission {
        IMMEDIATE,
        DELAYED,
        ZERO_DELAY,
        REPEATING;

        TaskHandle submit(Fixture fixture, Runnable work, Runnable retired) {
            return switch (this) {
                case IMMEDIATE -> fixture.scheduler.runFor(fixture.entity, work, retired);
                case DELAYED -> fixture.scheduler.runForLater(fixture.entity, work, retired, 3L);
                case ZERO_DELAY -> fixture.scheduler.runForLater(fixture.entity, work, retired, 0L);
                case REPEATING -> fixture.scheduler.runForAtFixedRate(fixture.entity, work, 0L, 2L);
            };
        }
    }

    private static final class Fixture {
        private Throwable failure;
        private int submissions;
        private Consumer<ScheduledTask> task;
        private final AtomicInteger cancellations = new AtomicInteger();
        private final ScheduledTask nativeTask = proxy(ScheduledTask.class, (method, args) -> {
            if (method.equals("cancel")) {
                cancellations.incrementAndGet();
                return null;
            }
            throw new AssertionError("Unexpected native task call: " + method);
        });
        private final EntityScheduler entityScheduler = proxy(EntityScheduler.class, (method, args) -> {
            if (!method.equals("run") && !method.equals("runDelayed") && !method.equals("runAtFixedRate")) {
                throw new AssertionError("Unexpected entity scheduler call: " + method);
            }
            submissions++;
            if (failure != null) {
                throw failure;
            }
            @SuppressWarnings("unchecked")
            Consumer<ScheduledTask> callback = (Consumer<ScheduledTask>) args[1];
            task = callback;
            return nativeTask;
        });
        private final Entity entity = proxy(Entity.class, (method, args) -> {
            if (method.equals("getScheduler")) {
                return entityScheduler;
            }
            throw new AssertionError("Unexpected entity call: " + method);
        });
        private final PaperScheduler scheduler = new PaperScheduler(
                proxy(Plugin.class, (method, args) -> {
                    if (method.equals("getLogger")) {
                        return Logger.getLogger(TestPaperSchedulerSubmissionFailure.class.getName());
                    }
                    throw new AssertionError("Unexpected plugin call: " + method);
                }),
                proxy(PlatformCompatibilityService.class, (method, args) -> {
                    if (method.equals("isRegionOwnedExecution")) {
                        return true;
                    }
                    throw new AssertionError("Unexpected platform call: " + method);
                }));
    }

    private interface Invocation {
        Object invoke(String method, Object[] args) throws Throwable;
    }

    private static <T> T proxy(Class<T> type, Invocation invocation) {
        return type.cast(Proxy.newProxyInstance(
                type.getClassLoader(),
                new Class<?>[] {type},
                (proxy, method, args) -> invocation.invoke(method.getName(), args)));
    }
}
