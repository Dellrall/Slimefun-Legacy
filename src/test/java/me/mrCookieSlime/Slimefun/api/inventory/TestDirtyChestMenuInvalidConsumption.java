package me.mrCookieSlime.Slimefun.api.inventory;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
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

/** Invalid or empty-slot consumption must neither create items nor schedule a save. */
class TestDirtyChestMenuInvalidConsumption {

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
    void consumingEmptySlotsDoesNotThrowOrDirty() {
        DirtyChestMenu menu = newMenu();
        long before = menu.captureChangeSequence();

        assertDoesNotThrow(() -> menu.consumeItem(0));
        assertDoesNotThrow(() -> menu.consumeItem(1, 3));
        assertDoesNotThrow(() -> menu.consumeItem(2, 1, true));

        assertNull(menu.getItemInSlot(0));
        assertNull(menu.getItemInSlot(1));
        assertNull(menu.getItemInSlot(2));
        assertEquals(before, menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    @Test
    void negativeOrZeroConsumptionDoesNotIncreaseItemsOrDirtyTheMenu() {
        DirtyChestMenu menu = newMenu();
        menu.replaceExistingItem(0, new ItemStack(Material.COBBLESTONE, 5));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();

        menu.consumeItem(0, -2);
        menu.consumeItem(0, 0);
        menu.consumeItem(0, -10, true);

        assertEquals(5, menu.getItemInSlot(0).getAmount());
        assertEquals(before, menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    @Test
    void zeroConsumptionDoesNotTransformAConsumable() {
        DirtyChestMenu menu = newMenu();
        menu.replaceExistingItem(0, new ItemStack(Material.POTION, 1));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();

        menu.consumeItem(0, 0, true);
        assertEquals(Material.POTION, menu.getItemInSlot(0).getType());
        assertEquals(1, menu.getItemInSlot(0).getAmount());
        assertEquals(before, menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    @Test
    void positiveConsumptionStillMutatesAndRequiresPersistence() {
        DirtyChestMenu menu = newMenu();
        menu.replaceExistingItem(0, new ItemStack(Material.COBBLESTONE, 5));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();

        menu.consumeItem(0, 2);

        assertEquals(3, menu.getItemInSlot(0).getAmount());
        assertTrue(menu.isDirty());
        assertTrue(menu.captureChangeSequence() > before);
    }

    private DirtyChestMenu newMenu() {
        DirtyChestMenu menu = new DirtyChestMenu(new TestPreset());
        menu.setSize(18);
        menu.acknowledgeChanges(menu.captureChangeSequence());
        assertFalse(menu.isDirty());
        return menu;
    }

    private static final class TestPreset extends BlockMenuPreset {

        private TestPreset() {
            super("TEST_DIRTY_INVALID_CONSUMPTION", "Consumption");
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
