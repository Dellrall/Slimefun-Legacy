package io.github.thebusybiscuit.slimefun4.core.networks.energy;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/** Presentation-state refresh checks must work even when a machine ticker runs at a fixed phase. */
class TestEnergyNetTransportRefresh {

    @Test
    void deadlinesAreReachedInsteadOfRequiringAnExactWorldTickPhase() {
        long nextRevalidation = 28L;
        int refreshed = 0;

        // A regulator called only at ticks 10, 30, 50 ... would never hit
        // (gameTime + regulator.hashCode()) % 20 == 0 for most hash values.
        for (long gameTime = 10L; gameTime <= 110L; gameTime += 20L) {
            if (EnergyNet.isTransportRefreshDue(gameTime, nextRevalidation)) {
                refreshed++;
                nextRevalidation = gameTime + 20L;
            }
        }

        assertEquals(5, refreshed);
        assertEquals(130L, nextRevalidation);
    }

    @Test
    void unchangedStateCanSkipRepeatedInspectionsBeforeItsDeadline() {
        assertFalse(EnergyNet.isTransportRefreshDue(100L, 120L));
        assertFalse(EnergyNet.isTransportRefreshDue(119L, 120L));
        assertTrue(EnergyNet.isTransportRefreshDue(120L, 120L));
        assertTrue(EnergyNet.isTransportRefreshDue(121L, 120L));
    }

    @Test
    void newNetworksAndRewoundWorldClocksRequireRevalidation() {
        assertTrue(EnergyNet.isTransportRefreshDue(0L, -1L));
        assertTrue(EnergyNet.isTransportRefreshDue(15L, 10020L));
        assertFalse(EnergyNet.isTransportRefreshDue(100L, 110L));
    }

    @Test
    void negativeRegulatorHashesStillProduceBoundedInitialDelays() {
        for (int hash : new int[] {Integer.MIN_VALUE, -19, -1, 0, 1, 19, Integer.MAX_VALUE}) {
            long initialDelay = 1L + Math.floorMod(hash, 20);
            assertTrue(initialDelay >= 1L && initialDelay <= 20L);
        }
    }
}
