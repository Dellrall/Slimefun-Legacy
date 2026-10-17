package io.github.thebusybiscuit.slimefun4.core.services.stability;

import java.util.UUID;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

class TestBackpackOpenRegistry {

    @Test
    void duplicateBackpackReservationDoesNotReleaseOriginalPlayer() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID first = UUID.randomUUID();
        UUID second = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(first, "uuid:backpack"));
        Assertions.assertFalse(registry.reserve(second, "uuid:backpack"));
        Assertions.assertTrue(registry.isOpening(first));
        Assertions.assertFalse(registry.isOpening(second));

        registry.release(first, "uuid:backpack");
        Assertions.assertTrue(registry.reserve(second, "uuid:backpack"));
    }

    @Test
    void wrongReservationKeyCannotUnlockBackpack() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID player = UUID.randomUUID();
        UUID other = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(player, "uuid:one"));
        registry.release(player, "uuid:two");
        Assertions.assertTrue(registry.isOpening(player));
        Assertions.assertFalse(registry.reserve(player, "uuid:two"));
        Assertions.assertFalse(registry.reserve(other, "uuid:one"));
    }

    @Test
    void activatedReservationRemainsExclusiveUntilClose() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID first = UUID.randomUUID();
        UUID second = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(first, "uuid:backpack"));
        Assertions.assertTrue(registry.activate(first, "uuid:backpack", "uuid:backpack"));
        Assertions.assertFalse(registry.isOpening(first));

        // The load is finished, but the backing backpack is still actively open.
        Assertions.assertFalse(registry.reserve(second, "uuid:backpack"));
        Assertions.assertFalse(registry.reserve(first, "uuid:other"));

        registry.release(first);
        Assertions.assertTrue(registry.reserve(second, "uuid:backpack"));
    }

    @Test
    void legacyReservationPromotesToCanonicalUuid() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID first = UUID.randomUUID();
        UUID second = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(first, "legacy:owner:18"));
        Assertions.assertTrue(registry.activate(first, "legacy:owner:18", "uuid:canonical"));
        Assertions.assertFalse(registry.isOpening(first));

        // A modern item representation of the same backing backpack must now be blocked.
        Assertions.assertFalse(registry.reserve(second, "uuid:canonical"));
        // The temporary legacy lookup key was replaced, so it is no longer globally locked.
        Assertions.assertTrue(registry.reserve(second, "legacy:owner:18"));
    }

    @Test
    void canonicalCollisionDoesNotStealExistingSession() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID legacyPlayer = UUID.randomUUID();
        UUID modernPlayer = UUID.randomUUID();
        UUID thirdPlayer = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(legacyPlayer, "legacy:owner:18"));
        Assertions.assertTrue(registry.reserve(modernPlayer, "uuid:canonical"));

        // The mixed legacy representation resolves to a UUID already owned by the modern request.
        Assertions.assertFalse(registry.activate(legacyPlayer, "legacy:owner:18", "uuid:canonical"));
        Assertions.assertTrue(registry.isOpening(legacyPlayer));

        registry.release(legacyPlayer);
        Assertions.assertTrue(registry.activate(modernPlayer, "uuid:canonical", "uuid:canonical"));
        Assertions.assertFalse(registry.reserve(thirdPlayer, "uuid:canonical"));

        registry.release(modernPlayer);
        Assertions.assertTrue(registry.reserve(thirdPlayer, "uuid:canonical"));
    }

    @Test
    void staleRequestCannotActivateOrReleaseSameKeySuccessor() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID player = UUID.randomUUID();
        UUID oldToken = UUID.randomUUID();
        UUID currentToken = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(player, "uuid:same", oldToken));
        Assertions.assertTrue(registry.releaseOwned(player, oldToken));
        Assertions.assertTrue(registry.reserve(player, "uuid:same", currentToken));

        Assertions.assertFalse(registry.activate(player, "uuid:same", "uuid:same", oldToken));
        Assertions.assertFalse(registry.releaseOwned(player, oldToken));
        Assertions.assertTrue(registry.ownsRequest(player, currentToken));
        Assertions.assertTrue(registry.isOpening(player));
        Assertions.assertFalse(registry.reserve(UUID.randomUUID(), "uuid:same"));
        Assertions.assertTrue(registry.activate(player, "uuid:same", "uuid:same", currentToken));
        Assertions.assertTrue(registry.releaseOwned(player, currentToken));
    }

    @Test
    void requestTokenSurvivesCanonicalPromotionUntilRelease() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID player = UUID.randomUUID();
        UUID token = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(player, "legacy:owner:18", token));
        Assertions.assertTrue(registry.activate(player, "legacy:owner:18", "uuid:canonical", token));
        Assertions.assertEquals(token, registry.getRequestToken(player));
        Assertions.assertTrue(registry.ownsRequest(player, token));
        Assertions.assertFalse(registry.isOpening(player));
        Assertions.assertTrue(registry.reserve(UUID.randomUUID(), "legacy:owner:18"));
        Assertions.assertFalse(registry.reserve(UUID.randomUUID(), "uuid:canonical"));

        Assertions.assertTrue(registry.releaseOwned(player, token));
        Assertions.assertNull(registry.getRequestToken(player));
        Assertions.assertTrue(registry.reserve(UUID.randomUUID(), "uuid:canonical"));
    }

    @Test
    void failedCanonicalActivationCannotReleaseAnotherPlayer() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID legacyPlayer = UUID.randomUUID();
        UUID modernPlayer = UUID.randomUUID();
        UUID legacyToken = UUID.randomUUID();
        UUID modernToken = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(legacyPlayer, "legacy:owner:18", legacyToken));
        Assertions.assertTrue(registry.reserve(modernPlayer, "uuid:canonical", modernToken));
        Assertions.assertFalse(registry.activate(legacyPlayer, "legacy:owner:18", "uuid:canonical", legacyToken));
        Assertions.assertFalse(registry.releaseOwned(modernPlayer, legacyToken));
        Assertions.assertTrue(registry.releaseOwned(legacyPlayer, legacyToken));
        Assertions.assertTrue(registry.ownsRequest(modernPlayer, modernToken));
        Assertions.assertTrue(registry.isOpening(modernPlayer));
        Assertions.assertFalse(registry.reserve(UUID.randomUUID(), "uuid:canonical"));
    }

    @Test
    void duplicateCompletionCannotReleaseDifferentKeySuccessor() {
        BackpackOpenRegistry registry = new BackpackOpenRegistry();
        UUID player = UUID.randomUUID();

        Assertions.assertTrue(registry.reserve(player, "uuid:first"));
        UUID oldToken = registry.getRequestToken(player);
        Assertions.assertTrue(registry.releaseOwned(player, oldToken));
        Assertions.assertTrue(registry.reserve(player, "uuid:second"));
        UUID currentToken = registry.getRequestToken(player);

        Assertions.assertFalse(registry.releaseOwned(player, oldToken));
        Assertions.assertFalse(registry.releaseOwned(player, null));
        Assertions.assertFalse(registry.ownsRequest(player, null));
        Assertions.assertTrue(registry.ownsRequest(player, currentToken));
        Assertions.assertFalse(registry.reserve(UUID.randomUUID(), "uuid:second"));
        Assertions.assertTrue(registry.releaseOwned(player, currentToken));
        Assertions.assertTrue(registry.reserve(UUID.randomUUID(), "uuid:second"));
    }
}
