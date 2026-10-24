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

/** Cargo merges must persist when legacy menu slot reads return detached ItemStack copies. */
class TestDirtyChestMenuDetachedMerge {

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
    void fullMergePersistsIntoActualInventoryWithoutExtraPresetCallback() {
        TestPreset preset = new TestPreset();
        DirtyChestMenu menu = newMenu(preset);
        menu.replaceExistingItem(0, new ItemStack(Material.STONE, 60));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();
        int callbacks = preset.changeCalls;
        ItemStack input = new ItemStack(Material.STONE, 4);

        assertNull(menu.pushItem(input, 0));
        assertEquals(64, menu.toInventory().getItem(0).getAmount());
        assertEquals(4, input.getAmount(), "The incoming stack must remain unchanged");
        assertEquals(callbacks, preset.changeCalls, "Merging must not invoke an extra preset callback");
        assertTrue(menu.isDirty(), "Successful merge must schedule persistence");
        assertTrue(menu.captureChangeSequence() > before);
    }

    @Test
    void partialMergeSavesEachChangedSlotAndReturnsOnlyRealRemainder() {
        DirtyChestMenu menu = newMenu(new TestPreset());
        menu.replaceExistingItem(0, new ItemStack(Material.COBBLESTONE, 63));
        menu.replaceExistingItem(1, new ItemStack(Material.COBBLESTONE, 62));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        ItemStack input = new ItemStack(Material.COBBLESTONE, 6);

        ItemStack remainder = menu.pushItem(input, 0, 1);

        assertNotNull(remainder);
        assertEquals(3, remainder.getAmount());
        assertEquals(64, menu.toInventory().getItem(0).getAmount());
        assertEquals(64, menu.toInventory().getItem(1).getAmount());
        assertEquals(6, input.getAmount());
        assertTrue(menu.isDirty());
    }

    @Test
    void rejectedMergeDoesNotMutateContentsOrDirtySequence() {
        DirtyChestMenu menu = newMenu(new TestPreset());
        menu.replaceExistingItem(0, new ItemStack(Material.DIAMOND, 64));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();
        ItemStack input = new ItemStack(Material.DIAMOND, 3);

        ItemStack remainder = menu.pushItem(input, 0);

        assertNotNull(remainder);
        assertEquals(3, remainder.getAmount());
        assertEquals(64, menu.toInventory().getItem(0).getAmount());
        assertEquals(before, menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    private static DirtyChestMenu newMenu(TestPreset preset) {
        DirtyChestMenu menu = new CopyOnReadMenu(preset);
        menu.setSize(18);
        menu.acknowledgeChanges(menu.captureChangeSequence());
        return menu;
    }

    private static final class CopyOnReadMenu extends DirtyChestMenu {

        private CopyOnReadMenu(BlockMenuPreset preset) {
            super(preset);
        }

        @Override
        public ItemStack getItemInSlot(int slot) {
            ItemStack stack = super.getItemInSlot(slot);
            return stack == null ? null : stack.clone();
        }
    }

    private static final class TestPreset extends BlockMenuPreset {

        private int changeCalls;

        private TestPreset() {
            super("TEST_DETACHED_LEGACY_MERGE", "Detached Merge");
        }

        @Override
        public void init() {
            setSize(18);
        }

        @Override
        protected ItemStack onItemStackChange(DirtyChestMenu menu, int slot, ItemStack previous, ItemStack next) {
            changeCalls++;
            return next;
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
