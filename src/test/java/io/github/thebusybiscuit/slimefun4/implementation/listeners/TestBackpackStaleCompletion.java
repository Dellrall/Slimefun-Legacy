package io.github.thebusybiscuit.slimefun4.implementation.listeners;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.thebusybiscuit.slimefun4.api.player.PlayerBackpack;
import io.github.thebusybiscuit.slimefun4.core.services.stability.BackpackOpenRegistry;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Arrays;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.bukkit.entity.Player;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

/** Exercises the actual compiled listener continuation after its original player has disconnected. */
class TestBackpackStaleCompletion {

    @ParameterizedTest
    @CsvSource({
        "load, different, false",
        "load, same, false",
        "load, different, true",
        "load, same, true",
        "profile, different, false",
        "profile, same, false",
        "profile, different, true",
        "profile, same, true"
    })
    void lateDisconnectedLoadCannotReleaseNewSession(String stage, String keyChoice, boolean active) throws Exception {
        BackpackListener listener = new BackpackListener();
        BackpackOpenRegistry registry = field(listener, "openRegistry");
        Map<UUID, UUID> backpacks = field(listener, "backpacks");
        UUID playerId = UUID.randomUUID();
        UUID newBackpack = UUID.randomUUID();
        UUID otherPlayer = UUID.randomUUID();
        String oldKey = "uuid:old-backpack";
        String newKey = keyChoice.equals("same") ? oldKey : "uuid:new-backpack";

        assertTrue(registry.reserve(playerId, oldKey));
        UUID oldToken = registry.getRequestToken(playerId);
        registry.release(playerId); // The quit event releases an in-flight load without a save.
        assertTrue(registry.reserve(playerId, newKey));
        if (active) {
            assertTrue(registry.activate(playerId, newKey, newKey));
            backpacks.put(playerId, newBackpack);
        }
        assertTrue(registry.reserve(otherPlayer, "uuid:unrelated"));

        // Native CraftPlayer.isOnline can return true for an old Player after the
        // same UUID reconnects. Ownership must reject this request before reading
        // any state from that old connection, regardless of its online result.
        invokeCompletion(listener, stage, playerId, oldKey, oldToken, true);

        assertTrue(registry.isOpening(otherPlayer), "An unrelated player must retain its request");
        if (active) {
            assertEquals(newBackpack, backpacks.get(playerId), "The new active inventory must retain listener state");
        } else {
            assertTrue(listener.isOpening(playerId), "The old load must not release the new pending request");
        }
        assertFalse(registry.reserve(UUID.randomUUID(), newKey), "The newer backpack must remain exclusively reserved");
    }

    @Test
    void disconnectedCurrentLoadReleasesOnlyItsOwnReservation() throws Exception {
        BackpackListener listener = new BackpackListener();
        BackpackOpenRegistry registry = field(listener, "openRegistry");
        UUID playerId = UUID.randomUUID();
        UUID otherPlayer = UUID.randomUUID();
        String key = "uuid:current";
        assertTrue(registry.reserve(playerId, key));
        assertTrue(registry.reserve(otherPlayer, "uuid:unrelated"));

        invokeCompletion(listener, "load", playerId, key, registry.getRequestToken(playerId));

        assertFalse(listener.isOpening(playerId));
        assertTrue(registry.isOpening(otherPlayer));
        assertTrue(registry.reserve(UUID.randomUUID(), key));
    }

    @Test
    void openCompletionCannotReleaseAReservationAlreadyHandedToPersistence() throws Exception {
        BackpackListener listener = new BackpackListener();
        BackpackOpenRegistry registry = field(listener, "openRegistry");
        Map<UUID, CompletableFuture<Void>> pendingSaves = field(listener, "pendingSaves");
        UUID playerId = UUID.randomUUID();
        String key = "uuid:closing-during-open";
        assertTrue(registry.reserve(playerId, key));
        UUID token = registry.getRequestToken(playerId);
        assertTrue(registry.activate(playerId, key, key, token));
        // An inventory event may close/save the backpack before bp.open returns.
        // Its enclosing open continuation still runs failure cleanup if the view was replaced.
        pendingSaves.put(playerId, new CompletableFuture<>());

        invokeCompletion(listener, "load", playerId, key, token);

        assertTrue(registry.ownsRequest(playerId, token), "The save must retain the canonical reservation");
        assertFalse(registry.reserve(UUID.randomUUID(), key), "A queued persistence write still blocks a stale reopen");
    }

    @ParameterizedTest
    @ValueSource(booleans = {false, true})
    void saveCompletionReleasesOnlyTheRequestAndFutureItStartedWith(boolean successor) throws Exception {
        BackpackListener listener = new BackpackListener();
        BackpackOpenRegistry registry = field(listener, "openRegistry");
        Map<UUID, UUID> backpacks = field(listener, "backpacks");
        Map<UUID, CompletableFuture<Void>> pendingSaves = field(listener, "pendingSaves");
        UUID playerId = UUID.randomUUID();
        UUID backpackId = UUID.randomUUID();
        String key = "uuid:" + backpackId;
        CompletableFuture<Void> oldSave = new CompletableFuture<>();
        assertTrue(registry.reserve(playerId, key));
        UUID oldToken = registry.getRequestToken(playerId);
        assertTrue(registry.activate(playerId, key, key));
        pendingSaves.put(playerId, oldSave);
        if (successor) {
            // A quit can finish the old session after its pending-save entry is removed,
            // while the save continuation has yet to run its final session cleanup.
            pendingSaves.remove(playerId, oldSave);
            assertTrue(registry.releaseOwned(playerId, oldToken));
            assertTrue(registry.reserve(playerId, key));
            assertTrue(registry.activate(playerId, key, key));
            backpacks.put(playerId, backpackId);
            pendingSaves.put(playerId, new CompletableFuture<>());
        }
        CompletableFuture<Void> currentSave = pendingSaves.get(playerId);
        Method completion = Arrays.stream(BackpackListener.class.getDeclaredMethods())
                .filter(method -> method.getName().startsWith("lambda$beginBackpackSave$"))
                .findFirst()
                .orElseThrow();
        completion.setAccessible(true);
        completion.invoke(listener, "close", playerId, oldSave, oldToken, null, null);

        if (successor) {
            assertEquals(currentSave, pendingSaves.get(playerId), "A late save must not remove a newer future");
            assertEquals(backpackId, backpacks.get(playerId));
            assertFalse(registry.reserve(UUID.randomUUID(), key));
        } else {
            assertFalse(pendingSaves.containsKey(playerId));
            assertTrue(registry.reserve(UUID.randomUUID(), key));
        }
    }

    private static void invokeCompletion(BackpackListener listener, String stage, UUID playerId, String key, UUID token)
            throws Exception {
        invokeCompletion(listener, stage, playerId, key, token, false);
    }

    private static void invokeCompletion(
            BackpackListener listener, String stage, UUID playerId, String key, UUID token, boolean stalePlayer)
            throws Exception {
        Player disconnected = (Player) Proxy.newProxyInstance(
                Player.class.getClassLoader(), new Class<?>[] {Player.class}, (proxy, method, args) -> {
                    return switch (method.getName()) {
                        case "isOnline" -> {
                            if (stalePlayer) {
                                throw new AssertionError(
                                        "A stale request must be rejected before reading old player state");
                            }
                            yield false;
                        }
                        case "getUniqueId" -> playerId;
                        default -> throw new AssertionError("Unexpected player access: " + method.getName());
                    };
                });
        Method continuation = Arrays.stream(BackpackListener.class.getDeclaredMethods())
                .filter(method -> stage.equals("profile")
                        ? method.getName().equals("openBackpackInternal")
                        : method.getName().startsWith("lambda$openBackpackInternal$")
                                && Arrays.asList(method.getParameterTypes()).contains(PlayerBackpack.class)
                                && Arrays.asList(method.getParameterTypes()).contains(Throwable.class))
                .findFirst()
                .orElseThrow();
        continuation.setAccessible(true);
        Class<?>[] types = continuation.getParameterTypes();
        Object[] arguments = new Object[types.length];
        int uuid = 0;
        for (int i = 0; i < types.length; i++) {
            if (types[i] == Player.class) arguments[i] = disconnected;
            else if (types[i] == String.class) arguments[i] = key;
            else if (types[i] == boolean.class) arguments[i] = true;
            else if (types[i] == UUID.class) arguments[i] = stage.equals("profile") || uuid++ > 0 ? token : playerId;
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
