package io.github.thebusybiscuit.slimefun4.implementation.listeners;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import io.github.thebusybiscuit.slimefun4.api.player.PlayerProfile;
import io.github.thebusybiscuit.slimefun4.core.services.scheduling.SlimefunScheduler;
import io.github.thebusybiscuit.slimefun4.core.services.stability.BackpackOpenRegistry;
import io.github.thebusybiscuit.slimefun4.implementation.Slimefun;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.bukkit.entity.Player;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockbukkit.mockbukkit.MockBukkit;

/** Exercises the actual initial profile continuation with controlled player ownership. */
class TestBackpackProfileDispatch {
    private InventoryReadTestPlugin fixture;

    @BeforeEach
    void setUp() {
        fixture = new InventoryReadTestPlugin(MockBukkit.mock());
    }

    @AfterEach
    void tearDown() {
        try {
            if (fixture != null) {
                try {
                    Slimefun.getProfiler().kill();
                } finally {
                    fixture.close();
                }
            }
        } finally {
            MockBukkit.unmock();
        }
    }

    @ParameterizedTest
    @ValueSource(booleans = {false, true})
    void profileCompletionReadsPlayerStateOnlyOnItsOwner(boolean initiallyOwned) throws Exception {
        BackpackListener listener = new BackpackListener();
        BackpackOpenRegistry registry = field(listener, "openRegistry");
        UUID playerId = UUID.randomUUID();
        String key = "uuid:profile-dispatch";
        assertTrue(registry.reserve(playerId, key));
        UUID token = registry.getRequestToken(playerId);
        AtomicBoolean owned = new AtomicBoolean(initiallyOwned);
        AtomicInteger playerReads = new AtomicInteger();
        List<Runnable> queued = new ArrayList<>();
        Player player = (Player) Proxy.newProxyInstance(
                Player.class.getClassLoader(), new Class<?>[] {Player.class}, (proxy, method, args) -> {
                    return switch (method.getName()) {
                        case "getUniqueId" -> playerId;
                        case "isOnline" -> {
                            assertTrue(owned.get(), "Profile completion read player state before entity ownership");
                            playerReads.incrementAndGet();
                            yield false;
                        }
                        default -> throw new AssertionError("Unexpected player access: " + method.getName());
                    };
                });
        SlimefunScheduler scheduler = (SlimefunScheduler) Proxy.newProxyInstance(
                SlimefunScheduler.class.getClassLoader(),
                new Class<?>[] {SlimefunScheduler.class},
                (proxy, method, args) -> {
                    return switch (method.getName()) {
                        case "isOwnedByCurrentRegion" -> {
                            assertSame(player, args[0]);
                            yield owned.get();
                        }
                        case "runFor" -> {
                            assertSame(player, args[0]);
                            queued.add((Runnable) args[1]);
                            yield null;
                        }
                        default -> throw new AssertionError("Unexpected scheduler access: " + method.getName());
                    };
                });
        Field schedulerField = Slimefun.class.getDeclaredField("schedulerService");
        schedulerField.setAccessible(true);
        Object previousScheduler = schedulerField.get(Slimefun.instance());

        try {
            schedulerField.set(Slimefun.instance(), scheduler);
            invokeProfileContinuation(listener, player, key, token);

            if (initiallyOwned) {
                assertEquals(1, playerReads.get());
                assertTrue(queued.isEmpty(), "Already-owned execution must remain inline");
            } else {
                assertEquals(0, playerReads.get());
                assertEquals(1, queued.size());
                assertTrue(registry.ownsRequest(playerId, token), "Queued owner work retains its request");
                owned.set(true);
                queued.removeFirst().run();
                assertEquals(1, playerReads.get());
            }

            assertTrue(queued.isEmpty());
            assertFalse(listener.isOpening(playerId));
            assertTrue(registry.reserve(UUID.randomUUID(), key), "The disconnected current request releases its key");
        } finally {
            schedulerField.set(Slimefun.instance(), previousScheduler);
        }
    }

    private static void invokeProfileContinuation(BackpackListener listener, Player player, String key, UUID token)
            throws Exception {
        Method continuation = Arrays.stream(BackpackListener.class.getDeclaredMethods())
                .filter(method -> method.getName().startsWith("lambda$openBackpack$")
                        && Arrays.asList(method.getParameterTypes()).contains(PlayerProfile.class))
                .findFirst()
                .orElseThrow();
        continuation.setAccessible(true);
        Class<?>[] types = continuation.getParameterTypes();
        Object[] arguments = new Object[types.length];
        for (int i = 0; i < types.length; i++) {
            if (types[i] == Player.class) arguments[i] = player;
            else if (types[i] == String.class) arguments[i] = key;
            else if (types[i] == boolean.class) arguments[i] = true;
            else if (types[i] == UUID.class) arguments[i] = token;
        }
        continuation.invoke(listener, arguments);
    }

    @SuppressWarnings("unchecked")
    private static <T> T field(Object target, String name) throws Exception {
        Field field = target.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return (T) field.get(target);
    }
}
