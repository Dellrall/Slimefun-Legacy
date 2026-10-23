package io.github.thebusybiscuit.slimefun4.core.services;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.InventoryContext;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;

/**
 * Regression for addons describing output slots 18-53 while a legacy menu
 * still has only 18 physical slots (0-17).
 */
class TestItemStackServiceSlotBounds {

    @BeforeEach
    void startServer() {
        MockBukkit.mock();
    }

    @AfterEach
    void stopServer() {
        MockBukkit.unmock();
    }

    @Test
    void completeExplicitSlotSelectionMustFitPhysicalInventory() {
        assertTrue(ItemStackService.hasValidSlotSelection(18));
        assertTrue(ItemStackService.hasValidSlotSelection(18, 0, 17));
        assertTrue(ItemStackService.hasValidSlotSelection(54, 18, 53));
        assertTrue(ItemStackService.hasValidSlotSelection(54, 18, 18, 53));
        assertFalse(ItemStackService.hasValidSlotSelection(18, 18));
        assertFalse(ItemStackService.hasValidSlotSelection(18, 0, 17, 18));
        assertFalse(ItemStackService.hasValidSlotSelection(54, 18, 54));
        assertFalse(ItemStackService.hasValidSlotSelection(54, -1, 0));
        assertFalse(ItemStackService.hasValidSlotSelection(-1));
    }

    @Test
    void smallerLegacyMenuRejectsCapacityChecksWithoutTouchingItems() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        ItemStack previous = new ItemStack(Material.DIAMOND, 7);
        inventory.setItem(0, previous.clone());
        ItemStack[] before = inventory.getContents();
        ItemStack output = new ItemStack(Material.STONE, 3);
        ItemStackService service = new ItemStackService();

        assertFalse(service.fits(inventory, output, InventoryContext.MACHINE_OUTPUT, 18));
        assertFalse(service.fitAll(inventory, new ItemStack[] {output}, InventoryContext.MACHINE_OUTPUT, 18));
        assertFalse(service.fitAll(inventory, new ItemStack[] {output}, InventoryContext.MACHINE_OUTPUT, 0, 17, 53));
        assertFalse(service.fitAll(inventory, new ItemStack[0], InventoryContext.MACHINE_OUTPUT, -1));
        assertArrayEquals(before, inventory.getContents(), "Invalid output slots may not mutate inventory");
        assertTrue(previous.equals(inventory.getItem(0)), "Preserved pre-existing item must be identical");
    }
}
