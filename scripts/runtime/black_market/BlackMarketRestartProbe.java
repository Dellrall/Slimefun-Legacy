package audit;

import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.logging.Level;
import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.inventory.ItemStack;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.java.JavaPlugin;

/** Non-shipping probe of the installed addon's store, not a copy of its implementation. */
public final class BlackMarketRestartProbe extends JavaPlugin {
    private static final UUID OWNER = UUID.fromString("8160641d-8db8-49cc-9716-d19e4da49bfb");
    private static final String PREFIX = "io.Yomicer.magicExpansion.utils.shop.BlackMarket";
    private Path data;
    private String token;
    private Class<?> storeType;
    private Class<?> cycleType;
    private Class<?> stateType;
    private Class<?> tradeType;
    private int assertions;

    @Override
    public void onEnable() {
        try {
            data = getDataFolder().toPath().toAbsolutePath().normalize();
            token = System.getProperty("sfl.blackmarket.probe.token", "");
            check(!token.isBlank() && Files.readString(data.resolve("authorization.txt")).equals(token),
                    "Disposable probe authorization missing");
            check(!Bukkit.getOnlineMode() && "127.0.0.1".equals(Bukkit.getIp()), "Loopback offline server required");
            check(Bukkit.getWorlds().getFirst().getName().equals("full-stack-smoke-world"),
                    "Unexpected world: production use forbidden");
            Plugin magic = Bukkit.getPluginManager().getPlugin("magicexpansion");
            check(magic != null && magic.isEnabled(), "Real MagicExpansion must be enabled");
            String expectedVersion = System.getProperty("sfl.blackmarket.probe.magic.version", "");
            check(!expectedVersion.isBlank(), "Expected MagicExpansion version missing");
            check(expectedVersion.equals(magic.getDescription().getVersion()),
                    "Unexpected candidate version: expected " + expectedVersion
                        + " but loaded " + magic.getDescription().getVersion());
            Plugin core = Bukkit.getPluginManager().getPlugin("Slimefun");
            check(core != null && core.isEnabled(), "Real Slimefun must be enabled");
            ClassLoader loader = magic.getClass().getClassLoader();
            storeType = Class.forName(PREFIX + "FileStore", true, loader);
            cycleType = Class.forName(PREFIX + "FileStore$Cycle", true, loader);
            stateType = Class.forName(PREFIX + "FileStore$PlayerState", true, loader);
            tradeType = Class.forName(PREFIX + "Manager$BlackMarketTrade", true, loader);
            check(storeType.getClassLoader() == loader, "Probe is not using installed addon classes");
            getLogger().info("BLACK_MARKET_PROBE READY");
        } catch (Exception failure) {
            throw new IllegalStateException("Black Market probe refused this environment", failure);
        }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof ConsoleCommandSender) || args.length != 1) return false;
        String phase = args[0];
        if (!Set.of("seed", "verify", "missing", "restored").contains(phase)) return false;
        Path result = data.resolve(phase + ".result");
        try {
            check(Bukkit.isPrimaryThread() && Bukkit.getOnlinePlayers().isEmpty(), "Empty synchronous fixture required");
            check(!Files.exists(result, LinkOption.NOFOLLOW_LINKS), "Stale result evidence");
            runPhase(phase);
            Files.writeString(result, "PASS\n" + phase + "\n" + token + "\n" + ProcessHandle.current().pid()
                    + "\n" + assertions + "\n", StandardOpenOption.CREATE_NEW);
            getLogger().info("BLACK_MARKET_PROBE PASS " + phase);
        } catch (Throwable failure) {
            getLogger().log(Level.SEVERE, "BLACK_MARKET_PROBE FAIL " + phase, failure);
            try {
                Files.writeString(result, "FAIL\n" + phase + "\n" + token + "\n" + failure + "\n",
                        StandardOpenOption.CREATE_NEW);
            } catch (IOException ignored) {
                getLogger().severe("Could not create failure evidence; this run must fail");
            }
        }
        return true;
    }

    private void runPhase(String phase) throws Exception {
        Path root = data.resolve("synthetic-ledger");
        Path marker = root.resolve("cycle.yml");
        Path player = root.resolve("players").resolve(OWNER + ".yml");
        Object store = construct(storeType, new Class<?>[] {Path.class}, root);
        long now = System.currentTimeMillis();
        if (phase.equals("seed")) {
            check(!Files.exists(root, LinkOption.NOFOLLOW_LINKS), "Seed requires genuinely new synthetic state");
            Object cycle = call(store, "loadOrCreate", new Class<?>[] {long.class}, now);
            check(load(store, cycle) == null, "Fresh synthetic player already exists");
            save(store, cycle, state(Set.of(1, 4), Set.of(1, 4, 7)));
            verifyState(load(store, cycle), Set.of(1, 4), Set.of(1, 4, 7));
            Files.write(data.resolve("cycle.baseline"), Files.readAllBytes(marker), StandardOpenOption.CREATE_NEW);
            Files.write(data.resolve("player.baseline"), Files.readAllBytes(player), StandardOpenOption.CREATE_NEW);
            return;
        }
        byte[] cycleBytes = Files.readAllBytes(data.resolve("cycle.baseline"));
        byte[] playerBytes = Files.readAllBytes(data.resolve("player.baseline"));
        if (phase.equals("missing")) {
            check(!Files.exists(marker, LinkOption.NOFOLLOW_LINKS), "Missing-marker fixture was not prepared");
            expectIo(() -> call(store, "loadOrCreate", new Class<?>[] {long.class}, now));
            expectIo(() -> load(store, null));
            expectIo(() -> save(store, null, state(Set.of(), Set.of())));
            expectIo(() -> call(store, "refresh", new Class<?>[] {cycleType, long.class}, null, now));
            check(!Files.exists(marker, LinkOption.NOFOLLOW_LINKS), "Missing cycle was recreated despite receipts");
            check(Arrays.equals(playerBytes, Files.readAllBytes(player)), "Missing cycle changed receipts");
            return;
        }
        Object cycle = call(store, "loadOrCreate", new Class<?>[] {long.class}, now);
        verifyState(load(store, cycle), Set.of(1, 4), Set.of(1, 4, 7));
        check(Arrays.equals(cycleBytes, Files.readAllBytes(marker)), "Restart rewrote cycle bytes");
        check(Arrays.equals(playerBytes, Files.readAllBytes(player)), "Restart rewrote receipt bytes");
        check(status(store, cycle).equals("MATCH"), "Restored cycle does not match");
        if (phase.equals("verify")) {
            byte[] changed = (new String(cycleBytes, StandardCharsets.UTF_8) + "\n# synthetic external rewrite\n")
                    .getBytes(StandardCharsets.UTF_8);
            Files.write(marker, changed);
            check(status(store, cycle).equals("SAME_CYCLE_DIFFERENT_BYTES"), "External rewrite not diagnosed");
            expectIo(() -> load(store, cycle));
            expectIo(() -> save(store, cycle, state(Set.of(), Set.of())));
            expectIo(() -> call(store, "refresh", new Class<?>[] {cycleType, long.class}, cycle, now));
            check(Arrays.equals(changed, Files.readAllBytes(marker)), "Diagnostics or refusal rewrote the marker");
            check(Arrays.equals(playerBytes, Files.readAllBytes(player)), "Conflict changed receipts");
            // Synthetic fixture only: restoring known bytes is not a production recovery procedure.
            Files.write(marker, cycleBytes);
            Files.delete(marker);
            expectIo(() -> call(store, "loadOrCreate", new Class<?>[] {long.class}, now));
            Files.write(marker, cycleBytes, StandardOpenOption.CREATE_NEW);
            expectIo(() -> save(store, cycle, state(Set.of(), Set.of())));
            expectIo(() -> call(store, "refresh", new Class<?>[] {cycleType, long.class}, cycle, now));
            check(Arrays.equals(playerBytes, Files.readAllBytes(player)), "Failed initialization retained authorization");
            return;
        }
        // The exact synthetic marker was restored while stopped, then loaded by a new JVM.
        Object fresh = call(store, "refresh", new Class<?>[] {cycleType, long.class}, cycle, now);
        check(!fresh.equals(cycle), "Normal rotation did not create a new cycle");
        byte[] rotated = Files.readAllBytes(marker);
        check(load(store, fresh) == null, "Old-cycle offers became current after normal rotation");
        expectIo(() -> call(store, "refresh", new Class<?>[] {cycleType, long.class}, cycle, now));
        check(Arrays.equals(rotated, Files.readAllBytes(marker)), "Stale refresh changed current cycle");
        check(Arrays.equals(playerBytes, Files.readAllBytes(player)), "Rotation erased previous receipts");
        save(store, fresh, state(Set.of(2), Set.of(2, 7)));
        verifyState(load(store, fresh), Set.of(2), Set.of(2, 7));
    }

    private Object load(Object store, Object cycle) throws Exception {
        return call(store, "loadPlayer", new Class<?>[] {UUID.class, cycleType}, OWNER, cycle);
    }

    private void save(Object store, Object cycle, Object state) throws Exception {
        call(store, "savePlayer", new Class<?>[] {UUID.class, cycleType, stateType}, OWNER, cycle, state);
    }

    private String status(Object store, Object cycle) throws Exception {
        Object inspection = call(store, "inspectCycle", new Class<?>[] {cycleType}, cycle);
        return call(inspection, "status", new Class<?>[0]).toString();
    }

    private Object state(Set<Integer> purchased, Set<Integer> revealed) throws Exception {
        List<Object> trades = new ArrayList<>();
        for (int slot = 0; slot < 10; slot++) {
            Object trade = construct(tradeType, new Class<?>[0]);
            boolean free = slot % 3 == 0;
            tradeType.getField("result").set(trade, rich(Material.DIAMOND, slot + 1, slot, "reward"));
            tradeType.getField("costs").set(trade,
                    free ? List.of() : List.of(rich(Material.EMERALD, slot + 2, slot, "cost")));
            tradeType.getField("isFree").setBoolean(trade, free);
            tradeType.getField("isHard").setBoolean(trade, slot % 2 == 1);
            trades.add(trade);
        }
        return construct(stateType, new Class<?>[] {List.class, Set.class, Set.class}, trades, purchased, revealed);
    }

    private void verifyState(Object loaded, Set<Integer> purchased, Set<Integer> revealed) throws Exception {
        check(loaded != null, "Saved state disappeared");
        check(purchased.equals(call(loaded, "purchased", new Class<?>[0])), "Purchase receipts changed");
        check(revealed.equals(call(loaded, "revealed", new Class<?>[0])), "Revealed slots changed");
        List<?> actual = (List<?>) call(loaded, "trades", new Class<?>[0]);
        List<?> expected = (List<?>) call(state(purchased, revealed), "trades", new Class<?>[0]);
        check(actual.size() == 10, "Offer count changed");
        for (int i = 0; i < 10; i++) {
            for (String field : List.of("result", "costs", "isFree", "isHard")) {
                check(tradeType.getField(field).get(expected.get(i)).equals(tradeType.getField(field).get(actual.get(i))),
                        "Offer " + i + " changed " + field + " including amount/metadata");
            }
        }
    }

    private ItemStack rich(Material type, int amount, int slot, String role) {
        ItemStack item = new ItemStack(type, amount);
        var meta = item.getItemMeta();
        meta.displayName(Component.text("Synthetic " + role + " " + slot));
        meta.lore(List.of(Component.text("Receipt restart fixture"), Component.text("Not a player item")));
        var pdc = meta.getPersistentDataContainer();
        pdc.set(NamespacedKey.fromString("sfl_probe:owner"), PersistentDataType.STRING, OWNER.toString());
        pdc.set(NamespacedKey.fromString("sfl_probe:slot"), PersistentDataType.INTEGER, slot);
        pdc.set(NamespacedKey.fromString("sfl_probe:sequence"), PersistentDataType.LONG, 9876543210L + slot);
        pdc.set(NamespacedKey.fromString("sfl_probe:bytes"), PersistentDataType.BYTE_ARRAY, new byte[] {1, 0, -1, (byte) slot});
        check(item.setItemMeta(meta), "Cannot set native item metadata");
        return item;
    }

    private static Object construct(Class<?> type, Class<?>[] types, Object... values) throws Exception {
        Constructor<?> constructor = type.getDeclaredConstructor(types);
        constructor.setAccessible(true);
        return constructor.newInstance(values);
    }

    private static Object call(Object receiver, String name, Class<?>[] types, Object... values) throws Exception {
        Method method = receiver.getClass().getDeclaredMethod(name, types);
        method.setAccessible(true);
        try {
            return method.invoke(receiver, values);
        } catch (InvocationTargetException wrapper) {
            if (wrapper.getCause() instanceof Exception exception) throw exception;
            if (wrapper.getCause() instanceof Error error) throw error;
            throw wrapper;
        }
    }

    @FunctionalInterface
    private interface Operation { void run() throws Exception; }

    private void expectIo(Operation operation) throws Exception {
        try {
            operation.run();
        } catch (IOException expected) {
            assertions++;
            return;
        }
        throw new AssertionError("Operation should have failed closed with IOException");
    }

    private void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
        assertions++;
    }
}
