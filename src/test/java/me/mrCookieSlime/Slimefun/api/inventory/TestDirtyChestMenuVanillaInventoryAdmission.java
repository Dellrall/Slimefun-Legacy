package me.mrCookieSlime.Slimefun.api.inventory;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import me.mrCookieSlime.Slimefun.api.item_transport.ItemTransportFlow;
import org.bukkit.Material;
import org.bukkit.block.Block;
import org.bukkit.entity.Player;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.inventory.ShulkerBoxInventoryMock;

/** Legacy Cargo menus must obey the same vanilla inventory-type rules as ItemStackService. */
class TestDirtyChestMenuVanillaInventoryAdmission {

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
    void nestedVanillaShulkerBoxCannotFitOrBePushedThroughAnySlotSelection() {
        Inventory inventory = new ShulkerBoxInventoryMock(null);
        BlockMenu menu = newMenu(inventory);
        inventory.setItem(0, new ItemStack(Material.DIAMOND, 3));
        ItemStack[] before = inventory.getContents();
        long beforeSequence = menu.captureChangeSequence();

        for (ItemStack forbidden : new ItemStack[] {
            new ItemStack(Material.SHULKER_BOX),
            new ItemStack(Material.WHITE_SHULKER_BOX)
        }) {
            for (int[] slots : new int[][] {{}, {1}, {1, 2}, {1, 1, 2}, {0, 1}}) {
                assertFalse(menu.fits(forbidden, slots),
                        "A forbidden vanilla item must never pass the Cargo preflight");
                ItemStack remainder = menu.pushItem(forbidden, slots);
                assertNotNull(remainder, "Rejected Cargo output must be returned intact");
                assertNotSame(forbidden, remainder, "Remainder must not alias the caller input");
                assertEquals(forbidden, remainder, "Complete forbidden output must remain available");
                assertArrayEquals(before, inventory.getContents(), "Rejected push must never modify the inventory");
                assertEquals(beforeSequence, menu.captureChangeSequence(),
                        "Rejected push must not record a persistence change");
                assertFalse(menu.isDirty());
            }
        }
    }

    @Test
    void ordinaryVanillaMaterialsStillFitAndInsertIntoShulkerInventory() {
        Inventory inventory = new ShulkerBoxInventoryMock(null);
        BlockMenu menu = newMenu(inventory);
        ItemStack stone = new ItemStack(Material.STONE, 5);

        assertTrue(menu.fits(stone, 1));
        assertNull(menu.pushItem(stone, 1));
        assertEquals(stone, inventory.getItem(1));
        assertEquals(5, stone.getAmount());
        assertTrue(menu.isDirty(), "Real insertion must schedule menu persistence");
    }

    @Test
    void admissionRejectionStillLeavesEarlierPhysicalSlotsUntouched() {
        Inventory inventory = new ShulkerBoxInventoryMock(null);
        BlockMenu menu = newMenu(inventory);
        ItemStack forbidden = new ItemStack(Material.BLUE_SHULKER_BOX, 1);
        ItemStack[] before = inventory.getContents();
        long sequence = menu.captureChangeSequence();

        assertFalse(menu.fits(forbidden, 1, 2, 3, 26));
        assertEquals(forbidden, menu.pushItem(forbidden, 1, 2, 3, 26));
        assertArrayEquals(before, inventory.getContents());
        assertEquals(sequence, menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    private static BlockMenu newMenu(Inventory inventory) {
        BlockMenu menu = new BlockMenu(new TestPreset(), null, inventory);
        menu.acknowledgeChanges(menu.captureChangeSequence());
        assertFalse(menu.isDirty());
        return menu;
    }

    private static final class TestPreset extends BlockMenuPreset {
        private TestPreset() {
            super("TEST_VANILLA_SHULKER_CARGO", "Vanilla Cargo Admission");
        }

        @Override
        public void init() {
            setSize(27);
        }

        @Override
        public boolean canOpen(Block block, Player player) {
            return true;
        }

        @Override
        public int[] getSlotsAccessedByItemTransport(ItemTransportFlow flow) {
            return new int[] {0, 1, 2, 3};
        }
    }
}
