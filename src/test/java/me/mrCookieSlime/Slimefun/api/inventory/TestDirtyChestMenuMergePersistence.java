package me.mrCookieSlime.Slimefun.api.inventory;

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
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;

/**
 * A cargo insertion into an existing physical stack must be included in the
 * next acknowledged block-inventory save, just like an empty-slot insertion.
 */
class TestDirtyChestMenuMergePersistence {

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
    void existingStackMergeRemainsDirtyUntilItsOwnSaveIsAcknowledged() {
        DirtyChestMenu menu = cleanMenu(11);
        long savedSequence = menu.captureChangeSequence();

        assertNull(menu.pushItem(new ItemStack(Material.COBBLESTONE, 5), 0));
        assertEquals(16, menu.getItemInSlot(0).getAmount());
        assertTrue(menu.isDirty(), "Merging an existing stack must schedule a save");
        assertTrue(menu.captureChangeSequence() > savedSequence);

        menu.acknowledgeChanges(savedSequence);
        assertTrue(menu.isDirty(), "An earlier save must not acknowledge the new merge");
        menu.acknowledgeChanges(menu.captureChangeSequence());
        assertFalse(menu.isDirty(), "The new save can acknowledge the merged contents");
    }

    @Test
    void fullStackWithNoMovementStaysCleanAndReturnsItsRemainder() {
        DirtyChestMenu menu = cleanMenu(64);
        long savedSequence = menu.captureChangeSequence();
        ItemStack incoming = new ItemStack(Material.COBBLESTONE, 3);

        ItemStack remainder = menu.pushItem(incoming, 0);
        assertNotNull(remainder);
        assertEquals(incoming, remainder);
        assertEquals(64, menu.getItemInSlot(0).getAmount());
        assertEquals(savedSequence, menu.captureChangeSequence());
        assertFalse(menu.isDirty(), "A rejected insertion must not queue an inventory save");
    }

    @Test
    void malformedSlotListDoesNotMutateOrDirtyAnyPhysicalStack() {
        DirtyChestMenu menu = cleanMenu(11);
        long savedSequence = menu.captureChangeSequence();
        ItemStack incoming = new ItemStack(Material.COBBLESTONE, 3);

        ItemStack remainder = menu.pushItem(incoming, 0, 18);
        assertNotNull(remainder);
        assertNotSame(incoming, remainder);
        assertEquals(incoming, remainder);
        assertEquals(11, menu.getItemInSlot(0).getAmount());
        assertEquals(savedSequence, menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    private DirtyChestMenu cleanMenu(int amount) {
        DirtyChestMenu menu = new DirtyChestMenu(new TestPreset());
        menu.setSize(18);
        menu.replaceExistingItem(0, new ItemStack(Material.COBBLESTONE, amount));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        assertFalse(menu.isDirty(), "The fixture starts from an acknowledged inventory");
        return menu;
    }

    private static final class TestPreset extends BlockMenuPreset {

        private TestPreset() {
            super("TEST_DIRTY_MERGE_PERSISTENCE", "Merge Persistence");
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
            return new int[] {0};
        }
    }
}
