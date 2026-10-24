package me.mrCookieSlime.Slimefun.api.inventory;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import io.github.thebusybiscuit.slimefun4.api.items.ItemGroup;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItem;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItemStack;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.ConsumeContext;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.ItemResult;
import io.github.thebusybiscuit.slimefun4.api.recipes.RecipeType;
import io.github.thebusybiscuit.slimefun4.implementation.Slimefun;
import java.util.concurrent.atomic.AtomicInteger;
import me.mrCookieSlime.Slimefun.api.item_transport.ItemTransportFlow;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.block.Block;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;

/** Handled virtual item consumption must record exactly one persisted menu change. */
class TestDirtyChestMenuVirtualConsumptionSequence {

    private static final String ID = "TEST_MENU_VIRTUAL_CONSUME_DIRTY";
    private InventoryReadTestPlugin fixture;
    private final AtomicInteger consumeCalls = new AtomicInteger();

    @BeforeEach
    void startServer() {
        fixture = new InventoryReadTestPlugin(MockBukkit.mock());
        SlimefunItem virtualItem = new SlimefunItem(
                new ItemGroup(
                        new NamespacedKey("slimefun", "virtual_consume_dirty_fixture"),
                        new ItemStack(Material.BOOK)),
                new SlimefunItemStack(ID, Material.DIAMOND, "Virtual consumption fixture"),
                RecipeType.ENHANCED_CRAFTING_TABLE,
                new ItemStack[9]);
        virtualItem.addItemHandler(new VirtualItemHandler() {
            @Override
            public boolean isVirtualItem(ItemStack stack) {
                return stack != null && stack.getType() == Material.DIAMOND;
            }

            @Override
            public ItemResult consume(ItemStack stack, int amount, boolean replaceConsumables, ConsumeContext context) {
                consumeCalls.incrementAndGet();
                int remaining = stack.getAmount() - amount;
                if (remaining <= 0) {
                    return ItemResult.handled(null);
                }

                ItemStack updated = stack.clone();
                updated.setAmount(remaining);
                return ItemResult.handled(updated);
            }
        });
        Slimefun.getRegistry().getSlimefunItemIds().put(ID, virtualItem);
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
    void partialVirtualConsumptionRecordsExactlyOneChange() {
        TestPreset preset = new TestPreset();
        DirtyChestMenu menu = newMenu(preset);
        menu.replaceExistingItem(0, virtualStack(4));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();
        int previousCallbacks = preset.changeCalls;

        menu.consumeItem(0, 2);

        ItemStack actual = menu.toInventory().getItem(0);
        assertNotNull(actual);
        assertEquals(2, actual.getAmount());
        assertEquals(1, consumeCalls.get(), "Virtual handler must be invoked once");
        assertEquals(previousCallbacks + 1, preset.changeCalls, "Preserve the existing preset callback");
        assertEquals(before + 1, menu.captureChangeSequence(), "One consume must record one change");
        assertEquals(1, menu.getUnsavedChanges());
        assertTrue(menu.isDirty());
        menu.acknowledgeChanges(menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    @Test
    void fullVirtualConsumptionClearsSlotAndRecordsOneChange() {
        TestPreset preset = new TestPreset();
        DirtyChestMenu menu = newMenu(preset);
        menu.replaceExistingItem(0, virtualStack(1));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();
        int callbacks = preset.changeCalls;

        menu.consumeItem(0, 1);

        assertNull(menu.toInventory().getItem(0));
        assertEquals(1, consumeCalls.get());
        assertEquals(callbacks + 1, preset.changeCalls, "Full removal keeps the preset callback");
        assertEquals(before + 1, menu.captureChangeSequence());
        assertEquals(1, menu.getUnsavedChanges());
        menu.acknowledgeChanges(menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    @Test
    void noOpAmountsDoNotInvokeVirtualHandlersOrDirtyMenu() {
        DirtyChestMenu menu = newMenu(new TestPreset());
        menu.replaceExistingItem(0, virtualStack(4));
        menu.acknowledgeChanges(menu.captureChangeSequence());
        long before = menu.captureChangeSequence();

        menu.consumeItem(0, 0);
        menu.consumeItem(0, -2);
        menu.consumeItem(1, 1);

        assertEquals(0, consumeCalls.get());
        assertEquals(4, menu.toInventory().getItem(0).getAmount());
        assertEquals(before, menu.captureChangeSequence());
        assertFalse(menu.isDirty());
    }

    private static ItemStack virtualStack(int amount) {
        ItemStack item = new ItemStack(Material.DIAMOND, amount);
        Slimefun.getItemDataService().setItemData(item, ID);
        assertNotNull(SlimefunItem.getByItem(item));
        return item;
    }

    private static DirtyChestMenu newMenu(TestPreset preset) {
        DirtyChestMenu menu = new DirtyChestMenu(preset);
        menu.setSize(18);
        menu.acknowledgeChanges(menu.captureChangeSequence());
        return menu;
    }

    private static final class TestPreset extends BlockMenuPreset {
        private int changeCalls;

        private TestPreset() {
            super("TEST_VIRTUAL_CONSUME_DIRTY_MENU", "Virtual Consumption");
        }

        @Override
        public void init() {
            setSize(18);
        }

        @Override
        protected ItemStack onItemStackChange(
                DirtyChestMenu menu, int slot, ItemStack previous, ItemStack next) {
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
