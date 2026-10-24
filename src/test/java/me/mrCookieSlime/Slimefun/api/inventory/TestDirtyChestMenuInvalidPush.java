package me.mrCookieSlime.Slimefun.api.inventory;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
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

/** Legacy Cargo preflight and insertion cannot accept malformed stack amounts. */
class TestDirtyChestMenuInvalidPush {

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
    void invalidAmountsCannotAdvertiseCapacityOrModifyExistingItems() {
        DirtyChestMenu menu = newMenu();
        menu.replaceExistingItem(0, new ItemStack(Material.COBBLESTONE, 10));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();

        for (int amount : new int[] {0, -3}) {
            ItemStack incoming = new ItemStack(Material.COBBLESTONE, 1);
            incoming.setAmount(amount);

            assertFalse(menu.fits(incoming, 0));
            assertFalse(menu.fits(incoming, 0, 1));
            assertFalse(menu.fits(incoming));

            for (int[] slots : new int[][] {{0}, {0, 1}, {1}, {}}) {
                ItemStack remainder = menu.pushItem(incoming, slots);
                assertNotNull(remainder, "Invalid output cannot be accepted");
                assertNotSame(incoming, remainder, "Remainder must not alias the input");
                assertEquals(incoming, remainder, "Entire invalid output must be retained");
                assertEquals(10, menu.getItemInSlot(0).getAmount());
                assertNull(menu.getItemInSlot(1));
                assertEquals(before, menu.captureChangeSequence());
                assertFalse(menu.isDirty(), "Rejected output must not schedule a save");
            }
            assertEquals(amount, incoming.getAmount());
        }
    }

    @Test
    void airCannotPassCapacityPreflightOrInsertion() {
        DirtyChestMenu menu = newMenu();
        ItemStack air = new ItemStack(Material.AIR);

        assertFalse(menu.fits(air, 0));
        assertFalse(menu.fits(air));
        assertThrows(IllegalArgumentException.class, () -> menu.pushItem(air, 0));
        assertFalse(menu.isDirty());
    }

    @Test
    void positiveInsertionStillMarksMenuDirtyAndPreservesInput() {
        DirtyChestMenu menu = newMenu();
        menu.replaceExistingItem(0, new ItemStack(Material.STONE, 5));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();
        ItemStack input = new ItemStack(Material.STONE, 3);

        assertTrue(menu.fits(input, 0));
        assertNull(menu.pushItem(input, 0));
        assertEquals(8, menu.getItemInSlot(0).getAmount());
        assertEquals(3, input.getAmount());
        assertTrue(menu.isDirty());
        assertTrue(menu.captureChangeSequence() > before);
    }

    private static DirtyChestMenu newMenu() {
        DirtyChestMenu menu = new DirtyChestMenu(new TestPreset());
        menu.setSize(18);
        menu.acknowledgeChanges(menu.captureChangeSequence());
        assertFalse(menu.isDirty());
        return menu;
    }

    private static final class TestPreset extends BlockMenuPreset {

        private TestPreset() {
            super("TEST_INVALID_PUSH", "Invalid Push");
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
