package io.github.thebusybiscuit.slimefun4.core.services;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
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

/** Multi-output machine preflight must not count the same physical slot twice. */
class TestItemStackServiceMultiOutputCapacity {

    @BeforeEach
    void startServer() {
        MockBukkit.mock();
    }

    @AfterEach
    void stopServer() {
        MockBukkit.unmock();
    }

    @Test
    void repeatedSlotsCannotFitSeparateOutputsInOnePhysicalStack() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        ItemStack[] results = {
            new ItemStack(Material.COBBLESTONE, 64), new ItemStack(Material.COBBLESTONE, 1)
        };
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        assertFalse(service.fitAll(inventory, results, InventoryContext.MACHINE_OUTPUT, 0, 0));
        assertTrue(service.fitAll(inventory, results, InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertTrue(service.fitAll(inventory, results, InventoryContext.MACHINE_OUTPUT, 0, 0, 1, 0));
        assertArrayEquals(before, inventory.getContents(), "Preflight must not insert recipe results");
        assertEquals(64, results[0].getAmount());
        assertEquals(1, results[1].getAmount());
    }

    @Test
    void oversizedCombinedOutputNeedsTwoDistinctPhysicalSlots() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        ItemStack[] results = {new ItemStack(Material.COBBLESTONE, 65)};
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        assertFalse(service.fitAll(inventory, results, InventoryContext.MACHINE_OUTPUT, 0));
        assertFalse(service.fitAll(inventory, results, InventoryContext.MACHINE_OUTPUT, 0, 0));
        assertTrue(service.fitAll(inventory, results, InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertArrayEquals(before, inventory.getContents(), "Preflight must not modify contents");
        assertEquals(65, results[0].getAmount());
    }

    @Test
    void existingPartialStackDoesNotCreateCapacityForTwoIndependentOutputs() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        inventory.setItem(0, new ItemStack(Material.STONE, 63));
        ItemStack[] results = {
            new ItemStack(Material.STONE, 1), new ItemStack(Material.STONE, 1)
        };
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        assertFalse(service.fitAll(inventory, results, InventoryContext.MACHINE_OUTPUT, 0, 0));
        assertTrue(service.fitAll(inventory, results, InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertArrayEquals(before, inventory.getContents(), "Preflight must not consume free capacity");
    }
}
