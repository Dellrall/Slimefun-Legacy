package io.github.thebusybiscuit.slimefun4.core.services;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

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

/** Vanilla inventory admission rules also apply to multi-output and snapshot capacity checks. */
class TestItemStackServiceVanillaContainerAdmission {

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
    void noNestedShulkerBoxInSingleOrMultipleMachineOutputs() {
        Inventory inventory = new ShulkerBoxInventoryMock(null);
        ItemStack nested = new ItemStack(Material.SHULKER_BOX, 1);
        ItemStack diamond = new ItemStack(Material.DIAMOND, 1);
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        assertFalse(service.fits(inventory, nested, InventoryContext.MACHINE_OUTPUT, 0));
        assertFalse(service.fitAll(inventory, new ItemStack[] {nested}, InventoryContext.MACHINE_OUTPUT, 0));
        assertFalse(service.fitAll(inventory, new ItemStack[] {nested, diamond},
                InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertFalse(service.fitAll(inventory, new ItemStack[] {diamond, nested},
                InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertFalse(service.fitAll(inventory, new ItemStack[] {nested, diamond},
                InventoryContext.MACHINE_OUTPUT, 0, 0, 1));
        assertFalse(service.fitAll(inventory, new ItemStack[] {nested, diamond},
                InventoryContext.MACHINE_OUTPUT));
        assertArrayEquals(before, inventory.getContents(), "Preflight must not change the shulker inventory");
    }

    @Test
    void coloredShulkerBoxesRemainDisallowedButOrdinaryOutputsFit() {
        Inventory inventory = new ShulkerBoxInventoryMock(null);
        ItemStack forbidden = new ItemStack(Material.WHITE_SHULKER_BOX, 1);
        ItemStack[] before = inventory.getContents();
        ItemStackService service = new ItemStackService();

        assertFalse(service.fitAll(inventory, new ItemStack[] {new ItemStack(Material.STONE, 1), forbidden},
                InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertTrue(service.fitAll(inventory, new ItemStack[] {new ItemStack(Material.STONE, 1),
                new ItemStack(Material.DIAMOND, 1)}, InventoryContext.MACHINE_OUTPUT, 0, 1));
        assertArrayEquals(before, inventory.getContents(), "Valid preflight must also be read-only");
    }
}
