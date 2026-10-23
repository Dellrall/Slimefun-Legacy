package me.mrCookieSlime.Slimefun.api.inventory;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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

/** Legacy Cargo capacity preflight must match an actual split-stack insertion. */
class TestDirtyChestMenuSplitCapacity {

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
    void splitAcrossTwoPartialPhysicalStacksSucceedsWithoutPreflightMutation() {
        DirtyChestMenu menu = newMenu();
        menu.replaceExistingItem(0, new ItemStack(Material.COBBLESTONE, 63));
        menu.replaceExistingItem(1, new ItemStack(Material.COBBLESTONE, 63));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long savedSequence = menu.captureChangeSequence();
        ItemStack output = new ItemStack(Material.COBBLESTONE, 2);

        assertFalse(menu.fits(output, 0), "One nearly-full slot cannot accept two more items");
        assertFalse(menu.fits(output, 0, 0), "A repeated slot is not extra capacity");
        assertTrue(menu.fits(output, 0, 1), "Two physical slots together have room");
        assertTrue(menu.fits(output, 0, 0, 1, 0), "Repeated declarations must not consume extra room");
        assertEquals(savedSequence, menu.captureChangeSequence(), "Preflight must not mark contents dirty");
        assertFalse(menu.isDirty(), "Capacity checks must not queue a save");
        assertEquals(63, menu.getItemInSlot(0).getAmount());
        assertEquals(63, menu.getItemInSlot(1).getAmount());

        assertNull(menu.pushItem(output, 0, 1));
        assertEquals(64, menu.getItemInSlot(0).getAmount());
        assertEquals(64, menu.getItemInSlot(1).getAmount());
        assertEquals(2, output.getAmount(), "The caller's output remains unchanged");
        assertTrue(menu.isDirty(), "The successful insertion must be persisted");
    }

    private DirtyChestMenu newMenu() {
        DirtyChestMenu menu = new DirtyChestMenu(new TestPreset());
        menu.setSize(18);
        return menu;
    }

    private static final class TestPreset extends BlockMenuPreset {

        private TestPreset() {
            super("TEST_DIRTY_SPLIT_CAPACITY", "Split Capacity");
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
