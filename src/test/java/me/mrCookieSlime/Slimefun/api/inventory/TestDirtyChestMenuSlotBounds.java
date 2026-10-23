package me.mrCookieSlime.Slimefun.api.inventory;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/**
 * Protects legacy 18-slot menus from addon output selectors configured for
 * larger physical menus; invalid mixed lists must fail as a whole.
 */
class TestDirtyChestMenuSlotBounds {

    @Test
    void legacyMenusRejectMalformedExplicitSelections() {
        assertFalse(DirtyChestMenu.hasValidSlotSelection(18, 18));
        assertFalse(DirtyChestMenu.hasValidSlotSelection(18, -1));
        assertFalse(DirtyChestMenu.hasValidSlotSelection(18, 0, 17, 18));
        assertFalse(DirtyChestMenu.hasValidSlotSelection(18, -1, 17));
        assertFalse(DirtyChestMenu.hasValidSlotSelection(18, 17, 53));
    }

    @Test
    void validSelectionsKeepHistoricalSlotSemantics() {
        assertTrue(DirtyChestMenu.hasValidSlotSelection(18));
        assertTrue(DirtyChestMenu.hasValidSlotSelection(18, 0, 17));
        assertTrue(DirtyChestMenu.hasValidSlotSelection(54));
        assertTrue(DirtyChestMenu.hasValidSlotSelection(54, 18, 53));
        assertTrue(DirtyChestMenu.hasValidSlotSelection(54, 18, 18, 53));
        assertFalse(DirtyChestMenu.hasValidSlotSelection(54, 53, 54));
        assertFalse(DirtyChestMenu.hasValidSlotSelection(-1));
    }
}
