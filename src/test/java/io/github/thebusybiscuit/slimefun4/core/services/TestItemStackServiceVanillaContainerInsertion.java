package io.github.thebusybiscuit.slimefun4.core.services;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.InventoryContext;
import org.bukkit.Material;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.inventory.ShulkerBoxInventoryMock;

/** Vanilla inventory admission must agree between preflight and actual insertion. */
class TestItemStackServiceVanillaContainerInsertion {

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
    void nestedShulkerReturnsCompleteRemainderForDefaultAndExplicitSlots() {
        Inventory inventory = new ShulkerBoxInventoryMock(null);
        inventory.setItem(0, new ItemStack(Material.DIAMOND, 3));
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        for (ItemStack forbidden : new ItemStack[] {
            new ItemStack(Material.SHULKER_BOX, 1),
            new ItemStack(Material.WHITE_SHULKER_BOX, 1)
        }) {
            for (int[] slots : new int[][] {{}, {1}, {1, 2}, {1, 1, 2}}) {
                ItemStack leftover = service.addItem(inventory, forbidden, InventoryContext.MACHINE_OUTPUT, slots);
                assertNotNull(leftover, "Rejected vanilla item must be returned");
                assertNotSame(forbidden, leftover, "Remainder must not alias the original item");
                assertEquals(forbidden, leftover, "Rejected item must remain completely intact");
                assertArrayEquals(before, inventory.getContents(), "Rejected insertion must not alter any slot");
            }
        }
    }

    @Test
    void ordinaryAllowedItemsStillInsertIntoShulkerInventories() {
        Inventory inventory = new ShulkerBoxInventoryMock(null);
        ItemStackService service = new ItemStackService();
        ItemStack stone = new ItemStack(Material.STONE, 4);
        ItemStack diamond = new ItemStack(Material.DIAMOND, 2);

        assertNull(service.addItem(inventory, stone, InventoryContext.MACHINE_OUTPUT, 1));
        assertEquals(stone, inventory.getItem(1));
        assertEquals(4, stone.getAmount(), "The input item must be unchanged");
        assertNull(service.addItem(inventory, diamond, InventoryContext.MACHINE_OUTPUT));
        assertEquals(diamond, inventory.getItem(0));
        assertEquals(2, diamond.getAmount());
    }

    @Test
    void malformedSlotsStillReturnFullRemainderWithoutMutation() {
        Inventory inventory = new ShulkerBoxInventoryMock(null);
        ItemStack output = new ItemStack(Material.STONE, 5);
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        ItemStack remainder = service.addItem(inventory, output, InventoryContext.MACHINE_OUTPUT, 0, 27);
        assertNotNull(remainder);
        assertNotSame(output, remainder);
        assertEquals(output, remainder);
        assertArrayEquals(before, inventory.getContents());
    }
}
