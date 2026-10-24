package io.github.thebusybiscuit.slimefun4.core.services;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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

/** Optional absent recipe outputs must be ignored without weakening physical slot checks. */
class TestItemStackServiceAbsentOutputs {

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
    void nullAndAirOutputsAreNoOpsWithoutChangingInventoryContents() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        inventory.setItem(0, new ItemStack(Material.DIAMOND, 64));
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        assertTrue(service.fitAll(inventory, new ItemStack[] {null}, InventoryContext.MACHINE_OUTPUT, 0));
        assertTrue(service.fitAll(
                inventory, new ItemStack[] {new ItemStack(Material.AIR)}, InventoryContext.MACHINE_OUTPUT, 0));
        assertTrue(service.fitAll(inventory, new ItemStack[] {null, new ItemStack(Material.AIR)},
                InventoryContext.MACHINE_OUTPUT, 0));
        assertTrue(service.fitAll(inventory, new ItemStack[0], InventoryContext.MACHINE_OUTPUT, 0));
        assertArrayEquals(before, inventory.getContents(), "No-op preflight must preserve inventory contents");
    }

    @Test
    void mixedAbsentAndRealOutputsStillRequirePhysicalCapacity() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        inventory.setItem(0, new ItemStack(Material.STONE, 64));
        ItemStack[] before = inventory.getContents();
        ItemStack realOutput = new ItemStack(Material.STONE, 1);
        ItemStack[] outputs = {null, new ItemStack(Material.AIR), realOutput};
        ItemStackService service = new ItemStackService();

        assertFalse(service.fitAll(inventory, outputs, InventoryContext.MACHINE_OUTPUT, 0));
        assertTrue(service.fitAll(inventory, outputs, InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertArrayEquals(before, inventory.getContents(), "Preflight must not insert a real output");
        assertEquals(1, realOutput.getAmount(), "Preflight must preserve source stack amounts");
    }

    @Test
    void absentOutputsDoNotBypassInvalidSlotSelections() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        assertFalse(service.fitAll(inventory, new ItemStack[] {null}, InventoryContext.MACHINE_OUTPUT, -1));
        assertFalse(service.fitAll(
                inventory, new ItemStack[] {new ItemStack(Material.AIR)}, InventoryContext.MACHINE_OUTPUT, 18));
        assertFalse(service.fitAll(
                inventory, new ItemStack[0], InventoryContext.MACHINE_OUTPUT, 0, 18));
        assertFalse(service.fitAll(inventory, new ItemStack[] {null, new ItemStack(Material.STONE, 1)},
                InventoryContext.MACHINE_OUTPUT, 0, 18));
        assertArrayEquals(before, inventory.getContents(), "Invalid selections must not touch inventory");
    }

    @Test
    void nullPlaceholderDoesNotMakeOversizedOutputFitOneSlot() {
        Inventory inventory = Bukkit.createInventory(null, 18);
        ItemStack[] before = inventory.getContents();
        ItemStack oversized = new ItemStack(Material.COBBLESTONE, 65);
        ItemStackService service = new ItemStackService();

        assertFalse(service.fitAll(inventory, new ItemStack[] {null, oversized},
                InventoryContext.MACHINE_OUTPUT, 0));
        assertTrue(service.fitAll(inventory, new ItemStack[] {null, oversized},
                InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertArrayEquals(before, inventory.getContents(), "Oversized output preflight must not mutate slots");
        assertEquals(65, oversized.getAmount());
    }
}
