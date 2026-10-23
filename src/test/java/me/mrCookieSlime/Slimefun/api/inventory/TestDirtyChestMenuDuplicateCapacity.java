package me.mrCookieSlime.Slimefun.api.inventory;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import me.mrCookieSlime.Slimefun.api.item_transport.ItemTransportFlow;
import org.bukkit.Material;
import org.bukkit.block.Block;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;

/** Duplicate addon output selectors must not fabricate additional physical stack capacity. */
class TestDirtyChestMenuDuplicateCapacity {

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
    void duplicateEmptySlotDoesNotAdvertiseMoreCapacityThanInsertionHas() {
        DirtyChestMenu menu = newMenu();
        ItemStack output = new ItemStack(Material.COBBLESTONE, 65);

        assertFalse(menu.fits(output, 0), "One physical slot holds at most 64 cobblestone");
        assertFalse(menu.fits(output, 0, 0), "Listing the same slot twice must not double its capacity");
        assertTrue(menu.fits(output, 0, 1), "Two different physical slots can fit the output");
        assertTrue(menu.fits(output, 0, 0, 1, 0), "Duplicates remain accepted but count only once");
        assertNull(menu.getItemInSlot(0), "Capacity preflight may not mutate the inventory");
        assertNull(menu.getItemInSlot(1));

        ItemStack remainder = menu.pushItem(output, 0, 0);
        assertNotNull(remainder);
        assertEquals(1, remainder.getAmount());
        assertEquals(64, menu.getItemInSlot(0).getAmount());
        assertEquals(65, output.getAmount(), "The caller's requested output remains unchanged");
    }

    @Test
    void malformedAndNormalSelectionsRetainTheirExistingBehavior() {
        DirtyChestMenu menu = newMenu();
        ItemStack stack = new ItemStack(Material.COBBLESTONE, 1);

        assertFalse(menu.fits(stack, 0, 18));
        assertTrue(menu.fits(stack, 0));
        assertTrue(menu.fits(stack, 0, 0));
        assertTrue(menu.fits(stack, 0, 17));
    }

    private DirtyChestMenu newMenu() {
        DirtyChestMenu menu = new DirtyChestMenu(new TestPreset());
        menu.setSize(18);
        return menu;
    }

    private static final class TestPreset extends BlockMenuPreset {

        private TestPreset() {
            super("TEST_DIRTY_DUPLICATE_CAPACITY", "Duplicate Capacity");
        }

        @Override
        public void init() {
            setSize(18);
        }

        @Override
        public boolean canOpen(Block block, Player player) {
            return true;
        }

        @Override
        public int[] getSlotsAccessedByItemTransport(ItemTransportFlow flow) {
            return new int[] {0, 1};
        }
    }
}
