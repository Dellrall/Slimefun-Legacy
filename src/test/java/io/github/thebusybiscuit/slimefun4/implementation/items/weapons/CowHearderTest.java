package io.github.thebusybiscuit.slimefun4.implementation.items.weapons;

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
    void rejectsBulkIssuance() {
        assertFalse(CowHearder.mayGive(true, true, 0));
        assertFalse(CowHearder.mayGive(true, true, 2));
        assertFalse(CowHearder.mayGive(true, true, 64));
        assertFalse(CowHearder.mayGive(true, true, -1));
    }
}
