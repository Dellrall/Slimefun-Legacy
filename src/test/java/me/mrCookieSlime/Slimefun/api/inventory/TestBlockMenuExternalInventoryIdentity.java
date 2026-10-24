package me.mrCookieSlime.Slimefun.api.inventory;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

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

/** Externally owned inventory backing must survive the first legacy menu slot read. */
class TestBlockMenuExternalInventoryIdentity {

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
    void firstReadAndWritePreserveSuppliedShulkerInventory() {
        Inventory actual = new ShulkerBoxInventoryMock(null);
        actual.setItem(0, new ItemStack(Material.DIAMOND, 5));
        BlockMenu menu = new BlockMenu(new TestPreset(), null, actual);

        assertEquals(27, menu.getSize(), "Menu must reserve all 27 physical slots");
        assertSame(actual, menu.toInventory());
        assertEquals(5, menu.getItemInSlot(0).getAmount());
        assertNull(menu.getItemInSlot(1));
        assertNull(menu.getItemInSlot(26));
        assertSame(actual, menu.toInventory(), "Lazy reads must not install a different chest");

        ItemStack output = new ItemStack(Material.STONE, 3);
        menu.replaceExistingItem(1, output);
        assertSame(actual, menu.toInventory());
        assertEquals(output, actual.getItem(1));
        assertEquals(5, actual.getItem(0).getAmount(), "Existing physical items must remain intact");
        assertEquals(3, output.getAmount());
    }

    @Test
    void firstSlotReadDoesNotDispatchOverridableReset() {
        Inventory actual = new ShulkerBoxInventoryMock(null);
        CountingResetMenu menu = new CountingResetMenu(new TestPreset(), actual);

        assertEquals(0, menu.resetCount);
        assertNull(menu.getItemInSlot(2));
        assertSame(actual, menu.toInventory());
        assertEquals(0, menu.resetCount, "A subclass reset must not occur during first access");

        menu.addItem(2, new ItemStack(Material.COBBLESTONE, 2));
        assertEquals(0, menu.resetCount);
        assertSame(actual, menu.toInventory());
        assertEquals(2, actual.getItem(2).getAmount());
    }

    @Test
    void fiveSlotExternalInventoryRetainsPhysicalBoundsAndIdentity() {
        Inventory hopperLike = mock(Inventory.class);
        ItemStack stored = new ItemStack(Material.IRON_INGOT, 2);
        when(hopperLike.getSize()).thenReturn(5);
        when(hopperLike.getItem(4)).thenReturn(stored);

        BlockMenu menu = new BlockMenu(new TestPreset(), null, hopperLike);

        assertEquals(9, menu.getSize(), "Legacy GUI rounds logical size up to nine");
        assertSame(hopperLike, menu.toInventory());
        assertSame(stored, menu.getItemInSlot(4));
        assertSame(hopperLike, menu.toInventory());
    }

    @Test
    void nullExternalInventoryRetainsHistoricalLazyInitialization() {
        BlockMenu menu = new BlockMenu(new TestPreset(), null, (Inventory) null);
        assertNull(menu.toInventory());
        assertNull(menu.getItemInSlot(0));
        assertFalse(menu.locked());
        assertEquals(9, menu.getSize());
    }

    private static final class CountingResetMenu extends BlockMenu {
        private int resetCount;

        private CountingResetMenu(BlockMenuPreset preset, Inventory inventory) {
            super(preset, null, inventory);
        }

        @Override
        public void reset(boolean update) {
            resetCount++;
            super.reset(update);
        }
    }

    private static final class TestPreset extends BlockMenuPreset {
        private TestPreset() {
            super("TEST_EXTERNAL_MENU_BACKING", "External Menu Backing");
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
            return new int[] {0, 1, 2};
        }
    }
}
