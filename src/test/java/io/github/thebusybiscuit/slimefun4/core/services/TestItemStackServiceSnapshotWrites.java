package io.github.thebusybiscuit.slimefun4.core.services;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import io.github.thebusybiscuit.slimefun4.api.items.ItemGroup;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItem;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItemStack;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.InventoryContext;
import io.github.thebusybiscuit.slimefun4.api.recipes.RecipeType;
import io.github.thebusybiscuit.slimefun4.implementation.Slimefun;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.util.concurrent.atomic.AtomicInteger;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;

/** Rejected Slimefun snapshot inserts must not rewrite an unchanged live inventory. */
class TestItemStackServiceSnapshotWrites {

    private static final String ID = "TEST_SNAPSHOT_WRITE_ITEM";
    private InventoryReadTestPlugin fixture;

    @BeforeEach
    void startServer() {
        fixture = new InventoryReadTestPlugin(MockBukkit.mock());
        Slimefun.getRegistry().getSlimefunItemIds().put(ID, new RegisteredItem());
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
    void rejectedSlimefunItemDoesNotRewriteClonedInventoryContents() {
        Inventory backing = Bukkit.createInventory(null, 18);
        backing.setItem(0, new ItemStack(Material.STONE, 64));
        ItemStack[] before = backing.getContents();
        AtomicInteger writes = new AtomicInteger();
        Inventory observed = trackContentWrites(backing, writes);
        ItemStack incoming = incomingItem(3);

        ItemStack remainder =
                new ItemStackService().addItem(observed, incoming, InventoryContext.MACHINE_OUTPUT, 0);

        assertNotNull(remainder);
        assertNotSame(incoming, remainder);
        assertEquals(incoming, remainder, "All rejected items must remain in the returned remainder");
        assertEquals(0, writes.get(), "No actual insertion must not write a cloned inventory");
        assertArrayEquals(before, backing.getContents());
        assertEquals(3, incoming.getAmount(), "The caller's stack must remain unchanged");
    }

    @Test
    void successfulSlimefunItemInsertStillCommitsSnapshotExactlyOnce() {
        Inventory backing = Bukkit.createInventory(null, 18);
        backing.setItem(0, new ItemStack(Material.STONE, 64));
        AtomicInteger writes = new AtomicInteger();
        Inventory observed = trackContentWrites(backing, writes);
        ItemStack incoming = incomingItem(3);

        ItemStack remainder =
                new ItemStackService().addItem(observed, incoming, InventoryContext.CARGO_INSERT, 1);

        assertNull(remainder);
        assertEquals(1, writes.get(), "A real insertion must commit the updated snapshot");
        assertEquals(incoming, backing.getItem(1));
        assertEquals(64, backing.getItem(0).getAmount());
        assertEquals(3, incoming.getAmount());
    }

    private static ItemStack incomingItem(int amount) {
        ItemStack stack = new ItemStack(Material.DIAMOND, amount);
        Slimefun.getItemDataService().setItemData(stack, ID);
        assertNotNull(SlimefunItem.getByItem(stack), "Fixture must use the Slimefun snapshot path");
        return stack;
    }

    private static Inventory trackContentWrites(Inventory backing, AtomicInteger writes) {
        return (Inventory) Proxy.newProxyInstance(
                Inventory.class.getClassLoader(),
                new Class<?>[] {Inventory.class},
                (proxy, method, args) -> {
                    if (method.getName().equals("setContents")) {
                        writes.incrementAndGet();
                    }
                    try {
                        return method.invoke(backing, args);
                    } catch (InvocationTargetException exception) {
                        throw exception.getCause();
                    }
                });
    }

    private static final class RegisteredItem extends SlimefunItem {

        private RegisteredItem() {
            super(
                    new ItemGroup(
                            new NamespacedKey("slimefun", "snapshot_write_fixture"),
                            new ItemStack(Material.BOOK)),
                    new SlimefunItemStack(ID, Material.DIAMOND, "Snapshot write fixture"),
                    RecipeType.ENHANCED_CRAFTING_TABLE,
                    new ItemStack[9]);
            addon = Slimefun.instance();
        }
    }
}
