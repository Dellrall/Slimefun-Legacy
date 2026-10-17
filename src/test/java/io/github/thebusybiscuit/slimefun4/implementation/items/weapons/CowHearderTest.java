package io.github.thebusybiscuit.slimefun4.implementation.items.weapons;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class CowHearderTest {

    @Test
    void allowsOnlyOperatorToOperatorIssuance() {
        assertTrue(CowHearder.mayGive(true, true, 1));

        assertFalse(CowHearder.mayGive(false, true, 1));
        assertFalse(CowHearder.mayGive(true, false, 1));
        assertFalse(CowHearder.mayGive(false, false, 1));
    }

    @Test
    void scalesLethalDamageToHealthWithoutOverflowingOrdinaryPlayerHits() {
        assertEquals(16_384.0D, CowHearder.strikeDamage(20.0D, 0.0D));
        assertEquals(16_384.0D, CowHearder.strikeDamage(20.0D, 16.0D));
        assertEquals(102_400.0D, CowHearder.strikeDamage(100.0D, 0.0D));
        assertEquals(1_048_576.0D, CowHearder.strikeDamage(1_000.0D, 24.0D));
    }

    @Test
    void boundsUnusualBossHealthInputs() {
        assertEquals(16_384.0D, CowHearder.strikeDamage(-5.0D, -1.0D));
        assertEquals(1_000_000_000_000.0D, CowHearder.strikeDamage(Double.MAX_VALUE, 0.0D));
        assertEquals(1_000_000_000_000.0D, CowHearder.strikeDamage(Double.POSITIVE_INFINITY, 0.0D));
        assertEquals(1_000_000_000_000.0D, CowHearder.strikeDamage(Double.NaN, 0.0D));
    }

    @Test
    void cowHearderCanDefeatAnotherAuthorizedWielder() {
        assertTrue(CowHearder.shouldBlockDamage(true, false));
        assertFalse(CowHearder.shouldBlockDamage(true, true));
        assertFalse(CowHearder.shouldBlockDamage(false, false));
        assertFalse(CowHearder.shouldBlockDamage(false, true));
    }

    @Test
    void rejectsBulkIssuance() {
        assertFalse(CowHearder.mayGive(true, true, 0));
        assertFalse(CowHearder.mayGive(true, true, 2));
        assertFalse(CowHearder.mayGive(true, true, 64));
        assertFalse(CowHearder.mayGive(true, true, -1));
    }
}
