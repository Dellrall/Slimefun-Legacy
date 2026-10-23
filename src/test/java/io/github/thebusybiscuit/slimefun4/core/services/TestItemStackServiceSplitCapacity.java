package io.github.thebusybiscuit.slimefun4.core.services;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.InventoryContext;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;

/** Preflight must accept outputs split across physical stacks without overstating capacity. */
class TestItemStackServiceSplitCapacity {

    private InventoryReadTestPlugin fixture;

    @BeforeEach
    void startServer() {
        fixture = new InventoryReadTestPlugin(MockBukkit.mock());
    }

    @AfterEach
    void stopServer() {
        try {
            if (fixture != null) {
                fixture.close();
            }
        } finally {
            MockBukkit.unmock();
        }
    }

    @Test
    void twoNearlyFullStacksHaveEnoughCombinedSpace() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        inventory.setItem(0, new ItemStack(Material.COBBLESTONE, 63));
        inventory.setItem(1, new ItemStack(Material.COBBLESTONE, 63));
        ItemStack[] before = inventory.getContents();
        ItemStack output = new ItemStack(Material.COBBLESTONE, 2);
        ItemStackService service = new ItemStackService();

        assertTrue(service.fits(inventory, output, InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertTrue(service.fits(inventory, output, InventoryContext.MACHINE_OUTPUT, 0, 0, 1, 0));
        assertTrue(service.fits(inventory, output, InventoryContext.MACHINE_OUTPUT));
        assertArrayEquals(before, inventory.getContents(), "Capacity checks must not change inventory contents");
        assertEquals(2, output.getAmount(), "Capacity checks must not alter the source stack");

        assertNull(service.addItem(inventory, output, InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertEquals(64, inventory.getItem(0).getAmount());
        assertEquals(64, inventory.getItem(1).getAmount());
        assertEquals(2, output.getAmount());
    }

    @Test
    void repeatedSlotAndIncompatibleContentsCannotInventFreeSpace() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        inventory.setItem(0, new ItemStack(Material.COBBLESTONE, 63));
        inventory.setItem(1, new ItemStack(Material.STONE, 63));
        ItemStack output = new ItemStack(Material.COBBLESTONE, 2);
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        assertFalse(service.fits(inventory, output, InventoryContext.MACHINE_OUTPUT, 0));
        assertFalse(service.fits(inventory, output, InventoryContext.MACHINE_OUTPUT, 0, 0));
        assertFalse(service.fits(inventory, output, InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertArrayEquals(before, inventory.getContents(), "A failed preflight must not mutate either stack");

        ItemStack remainder = service.addItem(inventory, output, InventoryContext.MACHINE_OUTPUT, 0, 0);
        assertNotNull(remainder);
        assertEquals(1, remainder.getAmount());
        assertEquals(64, inventory.getItem(0).getAmount());
        assertEquals(63, inventory.getItem(1).getAmount());
        assertEquals(2, output.getAmount());
    }
}
