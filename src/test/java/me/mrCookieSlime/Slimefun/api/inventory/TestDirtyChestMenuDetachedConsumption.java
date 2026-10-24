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

/** Legacy menu consumption must persist when getItemInSlot returns detached copies. */
class TestDirtyChestMenuDetachedConsumption {

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
    void partialConsumptionUpdatesStoredAmountAndDirtySequence() {
        TestPreset preset = new TestPreset();
        DirtyChestMenu menu = newMenu(preset);
        menu.replaceExistingItem(0, new ItemStack(Material.COBBLESTONE, 5));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();
        int callbacks = preset.changeCalls;

        menu.consumeItem(0, 2);

        assertEquals(3, menu.toInventory().getItem(0).getAmount(), "Consume must reach the physical slot");
        assertEquals(callbacks, preset.changeCalls, "Dough consumption must not gain a new preset callback");
        assertTrue(menu.isDirty());
        assertTrue(menu.captureChangeSequence() > before);
    }

    @Test
    void fullConsumptionClearsPhysicalSlot() {
        DirtyChestMenu menu = newMenu(new TestPreset());
        menu.replaceExistingItem(0, new ItemStack(Material.STONE, 2));
        menu.acknowledgeChanges(menu.captureChangeSequence());

        menu.consumeItem(0, 2);

        assertNull(menu.toInventory().getItem(0), "Consuming the last item must clear the real slot");
        assertTrue(menu.isDirty());
    }

    @Test
    void containerRemainderReplacesActualDetachedSlot() {
        TestPreset preset = new TestPreset();
        DirtyChestMenu menu = newMenu(preset);
        menu.replaceExistingItem(0, new ItemStack(Material.POTION, 1));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        int callbacks = preset.changeCalls;

        menu.consumeItem(0, 1, true);

        assertEquals(Material.GLASS_BOTTLE, menu.toInventory().getItem(0).getType());
        assertEquals(1, menu.toInventory().getItem(0).getAmount());
        assertEquals(callbacks, preset.changeCalls);
        assertTrue(menu.isDirty());
    }

    @Test
    void invalidConsumptionStillDoesNotMutateOrDirty() {
        DirtyChestMenu menu = newMenu(new TestPreset());
        menu.replaceExistingItem(0, new ItemStack(Material.STONE, 5));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();

        menu.consumeItem(0, 0);
        menu.consumeItem(0, -2);
        menu.consumeItem(1, 1);

        assertEquals(5, menu.toInventory().getItem(0).getAmount());
        assertNull(menu.toInventory().getItem(1));
        assertEquals(before, menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    private static DirtyChestMenu newMenu(TestPreset preset) {
        DirtyChestMenu menu = new DetachedReadMenu(preset);
        menu.setSize(18);
        menu.acknowledgeChanges(menu.captureChangeSequence());
        assertFalse(menu.isDirty());
        return menu;
    }

    private static final class DetachedReadMenu extends DirtyChestMenu {

        private DetachedReadMenu(BlockMenuPreset preset) {
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
            super("TEST_DETACHED_LEGACY_CONSUME", "Detached Consumption");
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
