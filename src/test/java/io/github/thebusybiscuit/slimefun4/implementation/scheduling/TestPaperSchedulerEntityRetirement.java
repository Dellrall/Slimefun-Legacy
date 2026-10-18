package io.github.thebusybiscuit.slimefun4.implementation.scheduling;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.thebusybiscuit.slimefun4.api.platform.PlatformCompatibilityService;
import io.github.thebusybiscuit.slimefun4.core.services.scheduling.TaskHandle;
import io.papermc.paper.threadedregions.scheduler.EntityScheduler;
import io.papermc.paper.threadedregions.scheduler.ScheduledTask;
import java.lang.reflect.Proxy;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;
import java.util.logging.Logger;
import org.bukkit.entity.Entity;
import org.bukkit.plugin.Plugin;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

/** Tests the production Folia adapter against the documented native entity-retirement boundaries. */
class TestPaperSchedulerEntityRetirement {

    @ParameterizedTest
    @EnumSource(Submission.class)
    void alreadyRetiredEntityCompletesCleanupWithoutRunningOwnedWork(Submission submission) {
        var fixture = new Fixture();
        fixture.reject = true;
        var completed = new CompletableFuture<Void>();
        var work = new AtomicInteger();
        var cleanup = new AtomicInteger();

        TaskHandle handle = submission.submit(fixture, work::incrementAndGet, () -> {
            cleanup.incrementAndGet();
            completed.complete(null);
        });

        assertTrue(handle.isCancelled(), "The rejected native task must remain cancelled");
        assertEquals(0, fixture.scheduler.getActiveTaskCount());
        assertEquals(0, work.get(), "A removed entity must never receive the owned work");
        assertEquals(1, cleanup.get(), "Native rejection invokes neither callback; the adapter must finish cleanup");
        assertTrue(completed.isDone(), "A caller waiting on its retirement cleanup must not be stranded");
    }

    @ParameterizedTest
    @EnumSource(Submission.class)
    void retirementAfterAcceptanceRunsCleanupExactlyOnce(Submission submission) {
        var fixture = new Fixture();
        var work = new AtomicInteger();
        var cleanup = new AtomicInteger();

        TaskHandle handle = submission.submit(fixture, work::incrementAndGet, cleanup::incrementAndGet);
        assertEquals(1, fixture.scheduler.getActiveTaskCount());
        fixture.retired.run();
        fixture.retired.run();
        fixture.task.accept(fixture.nativeTask);

        assertTrue(handle.isCancelled());
        assertEquals(0, fixture.scheduler.getActiveTaskCount());
        assertEquals(0, work.get());
        assertEquals(1, cleanup.get());
    }

    @ParameterizedTest
    @EnumSource(Submission.class)
    void acceptedEntityWorkKeepsItsNormalExecutionAndCancellationBehavior(Submission submission) {
        var fixture = new Fixture();
        var work = new AtomicInteger();
        var cleanup = new AtomicInteger();

        TaskHandle handle = submission.submit(fixture, work::incrementAndGet, cleanup::incrementAndGet);
        fixture.task.accept(fixture.nativeTask);

        assertFalse(handle.isCancelled());
        assertEquals(0, fixture.scheduler.getActiveTaskCount());
        assertEquals(1, work.get());
        assertEquals(0, cleanup.get());
    }

    enum Submission {
        IMMEDIATE,
        DELAYED,
        ZERO_DELAY;

        TaskHandle submit(Fixture fixture, Runnable work, Runnable retired) {
            return switch (this) {
                case IMMEDIATE -> fixture.scheduler.runFor(fixture.entity, work, retired);
                case DELAYED -> fixture.scheduler.runForLater(fixture.entity, work, retired, 3L);
                case ZERO_DELAY -> fixture.scheduler.runForLater(fixture.entity, work, retired, 0L);
            };
        }
    }

    private static final class Fixture {
        private boolean reject;
        private Consumer<ScheduledTask> task;
        private Runnable retired;
        private final ScheduledTask nativeTask = proxy(ScheduledTask.class, (method, args) -> switch (method) {
            case "cancel" -> null;
            default -> throw new AssertionError("Unexpected native task call: " + method);
        });
        private final EntityScheduler entityScheduler = proxy(EntityScheduler.class, (method, args) -> {
            if (!method.equals("run") && !method.equals("runDelayed")) {
                throw new AssertionError("Unexpected entity scheduler call: " + method);
            }
            @SuppressWarnings("unchecked")
            Consumer<ScheduledTask> callback = (Consumer<ScheduledTask>) args[1];
            task = callback;
            retired = (Runnable) args[2];
            return reject ? null : nativeTask;
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
                        return Logger.getLogger(TestPaperSchedulerEntityRetirement.class.getName());
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
        Object invoke(String method, Object[] args);
    }

    private static <T> T proxy(Class<T> type, Invocation invocation) {
        return type.cast(Proxy.newProxyInstance(
                type.getClassLoader(),
                new Class<?>[] {type},
                (proxy, method, args) -> invocation.invoke(method.getName(), args)));
    }
}
