package io.github.wickidcow.validation;

import io.github.thebusybiscuit.slimefun4.core.services.scheduling.TaskHandle;
import io.github.thebusybiscuit.slimefun4.implementation.Slimefun;
import io.github.thebusybiscuit.slimefun4.implementation.scheduling.PaperScheduler;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.ArmorStand;
import org.bukkit.entity.Entity;
import org.bukkit.plugin.java.JavaPlugin;

/** Disposable native lifecycle proof. Never install on a production server. */
public final class NativeEntityRetirementProbe extends JavaPlugin {
    private static final String WORLD = "retirement-probe-world";
    private final Map<String, Observation> observations = new LinkedHashMap<>();
    private final List<Entity> entities = new ArrayList<>();
    private final List<String> failures = new ArrayList<>();
    private PaperScheduler scheduler;
    private boolean folia;
    private boolean started;
    private boolean nativeRejected;
    private int assertions;
    private String token;
    private String coreSource;
    private String coreVersion;

    @Override
    public void onEnable() {
        token = System.getProperty("sfl.native.retirement.token", "");
        UUID.fromString(token);
        if (Bukkit.getWorld(WORLD) == null) throw new IllegalStateException("Exact disposable world required");
        coreVersion = Slimefun.instance().getPluginMeta().getVersion();
        if (!coreVersion.equals(System.getProperty("sfl.native.retirement.version", "")))
            throw new IllegalStateException("Loaded core version mismatch");
        Properties git = new Properties();
        try (InputStream input = Slimefun.instance().getResource("git.properties")) {
            if (input == null) throw new IllegalStateException("Loaded core source is absent");
            git.load(input);
        } catch (java.io.IOException failure) {
            throw new IllegalStateException("Cannot read loaded core source", failure);
        }
        coreSource = git.getProperty("git.source.commit", "");
        if (!coreSource.matches("[0-9a-f]{40}")
                || !coreSource.equals(System.getProperty("sfl.native.retirement.source", ""))
                || !coreSource.equals(git.getProperty("git.commit.id")))
            throw new IllegalStateException("Loaded core source mismatch");
        scheduler = new PaperScheduler(this);
        folia = scheduler.isFolia();
        String expectedSoftware = System.getProperty("sfl.native.retirement.software", "");
        String expectedMinecraft = System.getProperty("sfl.native.retirement.minecraft", "");
        String expectedBuild = System.getProperty("sfl.native.retirement.build", "");
        if (!Bukkit.getName().equals(expectedSoftware)
                || !Bukkit.getMinecraftVersion().equals(expectedMinecraft)
                || !Bukkit.getVersion().startsWith(expectedMinecraft + "-" + expectedBuild + "-")
                || folia != expectedSoftware.equals("Folia")
                || Slimefun.getSchedulerService().isFolia() != folia)
            throw new IllegalStateException("Loaded native platform mismatch");
    }

    @Override
    public void onDisable() {
        if (!started) return;
        try {
            Files.writeString(
                    getDataFolder().toPath().resolve("normal-shutdown.json"),
                    "{\"token\":\"" + token + "\",\"server_stopping\":"
                            + Bukkit.getServer().isStopping() + "}\n");
        } catch (java.io.IOException failure) {
            throw new IllegalStateException("Cannot write native shutdown receipt", failure);
        }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof org.bukkit.command.ConsoleCommandSender) || started || args.length != 0) return false;
        started = true;
        owner(
                () -> {
                    try {
                        exercise();
                        owner(this::verify, 30L);
                    } catch (Throwable failure) {
                        failures.add("unexpected:" + failure.getClass().getName());
                        getLogger().log(java.util.logging.Level.SEVERE, "RETIREMENT_PROBE unexpected failure", failure);
                        writeResult();
                    }
                },
                1L);
        return true;
    }

    private void owner(Runnable runnable, long delay) {
        World world = Bukkit.getWorld(WORLD);
        if (folia) Bukkit.getRegionScheduler().runDelayed(this, world, 0, 0, ignored -> runnable.run(), delay);
        else Bukkit.getScheduler().runTaskLater(this, runnable, delay);
    }

    private ArmorStand spawn() {
        World world = Bukkit.getWorld(WORLD);
        world.getChunkAt(0, 0).addPluginChunkTicket(this);
        ArmorStand entity = world.spawn(new Location(world, 8.5, 80.0, 8.5), ArmorStand.class);
        entity.setGravity(false);
        entity.setInvulnerable(true);
        entities.add(entity);
        return entity;
    }

    private Observation observation(String name) {
        Observation value = new Observation();
        observations.put(name, value);
        return value;
    }

    private void exercise() {
        require(scheduler.getActiveTaskCount() == 0, "initial_active_handles");
        ArmorStand removed = spawn();
        removed.remove();
        if (folia) {
            nativeRejected = removed.getScheduler()
                            .run(
                                    this,
                                    ignored -> failures.add("unexpected_native_work"),
                                    () -> failures.add("unexpected_native_retirement"))
                    == null;
            require(nativeRejected, "native_rejected_removed_entity");
        }
        Observation immediate = observation("rejected_immediate");
        immediate.handle =
                scheduler.runFor(removed, immediate.work::incrementAndGet, immediate.retired::incrementAndGet);
        Observation delayed = observation("rejected_delayed");
        delayed.handle =
                scheduler.runForLater(removed, delayed.work::incrementAndGet, delayed.retired::incrementAndGet, 5L);
        Observation zero = observation("rejected_zero_delay");
        zero.handle = scheduler.runForLater(removed, zero.work::incrementAndGet, zero.retired::incrementAndGet, 0L);

        ArmorStand live = spawn();
        Observation liveImmediate = observation("live_immediate");
        liveImmediate.handle =
                scheduler.runFor(live, () -> ownedWork(live, liveImmediate), liveImmediate.retired::incrementAndGet);
        Observation liveDelayed = observation("live_delayed");
        liveDelayed.handle = scheduler.runForLater(
                live, () -> ownedWork(live, liveDelayed), liveDelayed.retired::incrementAndGet, 5L);

        ArmorStand retiring = spawn();
        Observation pending = observation("retired_after_acceptance");
        pending.handle =
                scheduler.runForLater(retiring, pending.work::incrementAndGet, pending.retired::incrementAndGet, 5L);
        retiring.remove();

        ArmorStand cancelledEntity = spawn();
        Observation cancelled = observation("explicitly_cancelled");
        cancelled.handle = scheduler.runForLater(
                cancelledEntity, cancelled.work::incrementAndGet, cancelled.retired::incrementAndGet, 5L);
        cancelled.handle.cancel();
        cancelled.handle.cancel();
        cancelledEntity.remove();
    }

    private void ownedWork(Entity entity, Observation value) {
        value.work.incrementAndGet();
        if (scheduler.isOwnedByCurrentRegion(entity)) value.owned.incrementAndGet();
    }

    private void verify() {
        try {
            for (Map.Entry<String, Observation> entry : observations.entrySet()) {
                String name = entry.getKey();
                Observation value = entry.getValue();
                boolean cancelled = name.equals("explicitly_cancelled");
                boolean retired = folia && (name.startsWith("rejected_") || name.equals("retired_after_acceptance"));
                require(value.work.get() == (retired || cancelled ? 0 : 1), name + ":work");
                require(value.retired.get() == (retired ? 1 : 0), name + ":retired");
                require(value.handle.isCancelled() == (retired || cancelled), name + ":cancelled");
                if (name.startsWith("live_")) require(value.owned.get() == 1, name + ":owner");
            }
            require(scheduler.getActiveTaskCount() == 0, "final_active_handles");
            for (Entity entity : entities) if (entity.isValid()) entity.remove();
            require(scheduler.getActiveTaskCount() == 0, "cleanup_active_handles");
            writeResult();
        } catch (Throwable failure) {
            failures.add("unexpected:" + failure.getClass().getName());
            getLogger().log(java.util.logging.Level.SEVERE, "RETIREMENT_PROBE unexpected failure", failure);
            writeResult();
        }
    }

    private void require(boolean condition, String label) {
        assertions++;
        if (!condition) failures.add(label);
    }

    private void writeResult() {
        try {
            StringBuilder out = new StringBuilder("{\n  \"schema\": 1,\n  \"status\": \"")
                    .append(failures.isEmpty() ? "PASS" : "FAIL")
                    .append("\",\n  \"token\": \"")
                    .append(token)
                    .append("\",\n  \"core_source\": \"")
                    .append(coreSource)
                    .append("\",\n  \"core_version\": \"")
                    .append(coreVersion)
                    .append("\",\n  \"software\": \"")
                    .append(Bukkit.getName())
                    .append("\",\n  \"minecraft\": \"")
                    .append(Bukkit.getMinecraftVersion())
                    .append("\",\n  \"server_version\": \"")
                    .append(Bukkit.getVersion())
                    .append("\",\n  \"folia\": ")
                    .append(folia)
                    .append(",\n  \"native_removed_entity_rejected\": ")
                    .append(nativeRejected)
                    .append(",\n  \"active_handles\": ")
                    .append(scheduler.getActiveTaskCount())
                    .append(",\n  \"assertions\": ")
                    .append(assertions)
                    .append(",\n  \"cases\": {\n");
            int index = 0;
            for (Map.Entry<String, Observation> entry : observations.entrySet()) {
                if (index++ > 0) out.append(",\n");
                Observation value = entry.getValue();
                out.append("    \"")
                        .append(entry.getKey())
                        .append("\": {\"work\": ")
                        .append(value.work)
                        .append(", \"retired\": ")
                        .append(value.retired)
                        .append(", \"owned\": ")
                        .append(value.owned)
                        .append(", \"cancelled\": ")
                        .append(value.handle != null && value.handle.isCancelled())
                        .append("}");
            }
            out.append("\n  },\n  \"failures\": [");
            for (int i = 0; i < failures.size(); i++) {
                if (i > 0) out.append(", ");
                out.append('"').append(failures.get(i)).append('"');
            }
            out.append("]\n}\n");
            Path result = getDataFolder().toPath().resolve("result.json");
            Files.createDirectories(result.getParent());
            Files.writeString(result, out.toString());
            getLogger()
                    .info("RETIREMENT_PROBE " + (failures.isEmpty() ? "PASS" : "FAIL") + " assertions=" + assertions);
        } catch (Exception failure) {
            throw new IllegalStateException("Cannot write native retirement evidence", failure);
        }
    }

    private static final class Observation {
        private final AtomicInteger work = new AtomicInteger();
        private final AtomicInteger retired = new AtomicInteger();
        private final AtomicInteger owned = new AtomicInteger();
        private TaskHandle handle;
    }
}
