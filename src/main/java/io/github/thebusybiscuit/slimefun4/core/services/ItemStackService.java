package io.github.thebusybiscuit.slimefun4.core.services;

import io.github.bakedlibs.dough.inventory.InvUtils;
import io.github.bakedlibs.dough.items.ItemUtils;
import io.github.thebusybiscuit.slimefun4.api.items.ItemHandler;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItem;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.AdmissionResult;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.ComparisonResult;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.ConsumeContext;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.InventoryContext;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.ItemResult;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.MatchContext;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.RemainderContext;
import io.github.thebusybiscuit.slimefun4.utils.SlimefunUtils;
import io.github.thebusybiscuit.slimefun4.utils.itemstack.ItemStackWrapper;
import java.util.Arrays;
import java.util.Map;
import java.util.Optional;
import java.util.function.Predicate;
import javax.annotation.Nonnull;
import javax.annotation.Nullable;
import org.apache.commons.lang.Validate;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;

public final class ItemStackService {

    public boolean isVirtualItem(@Nullable ItemStack item) {
        return resolveHandler(item) != null;
    }

    public @Nonnull ComparisonResult matches(
            @Nullable ItemStack left, @Nullable ItemStack right, @Nonnull MatchContext context) {
        VirtualItemHandler leftHandler = resolveHandler(left);
        VirtualItemHandler rightHandler = resolveHandler(right);

        if (leftHandler == null && rightHandler == null) {
            return ComparisonResult.NOT_HANDLED;
        }

        if (leftHandler != null && rightHandler != null) {
            if (leftHandler == rightHandler) {
                return leftHandler.matches(left, right, context);
            }

            ComparisonResult leftResult = leftHandler.matches(left, right, context);
            if (leftResult != ComparisonResult.NOT_HANDLED) {
                return leftResult;
            }

            ComparisonResult rightResult = rightHandler.matches(left, right, context);
            if (rightResult != ComparisonResult.NOT_HANDLED) {
                return rightResult;
            }

            return ComparisonResult.NO_MATCH;
        }

        return (leftHandler != null ? leftHandler : rightHandler).matches(left, right, context);
    }

    public boolean isSimilar(
            @Nullable ItemStack left,
            @Nullable ItemStack right,
            @Nonnull MatchContext context,
            boolean checkLore,
            boolean checkAmount) {
        ComparisonResult comparison = matches(left, right, context);
        if (comparison == ComparisonResult.MATCH) {
            return true;
        }

        if (comparison == ComparisonResult.NO_MATCH) {
            return false;
        }

        return SlimefunUtils.isItemSimilarWithoutVirtualItems(left, right, checkLore, checkAmount);
    }

    public boolean matchesPredicate(
            @Nonnull ItemStack item, @Nonnull Predicate<ItemStack> predicate, @Nonnull MatchContext context) {
        VirtualItemHandler handler = resolveHandler(item);
        if (handler != null) {
            ComparisonResult comparison = handler.matchesPredicate(item, predicate, context);
            if (comparison == ComparisonResult.MATCH) {
                return true;
            }

            if (comparison == ComparisonResult.NO_MATCH) {
                return false;
            }
        }

        return predicate.test(item);
    }

    public int getMaxStackSize(@Nonnull ItemStack item, @Nonnull InventoryContext context, int defaultMaxStackSize) {
        Validate.notNull(item, "The item cannot be null");

        VirtualItemHandler handler = resolveHandler(item);
        if (handler == null) {
            return defaultMaxStackSize;
        }

        return Math.max(1, handler.getMaxStackSize(item, context, defaultMaxStackSize));
    }

    public @Nonnull AdmissionResult allows(@Nonnull ItemStack item, @Nonnull InventoryContext context) {
        VirtualItemHandler handler = resolveHandler(item);
        if (handler == null) {
            return AdmissionResult.NOT_HANDLED;
        }

        return handler.allows(item, context);
    }

    public boolean canInsertIntoEmptySlot(@Nonnull ItemStack item, @Nonnull InventoryContext context) {
        return allows(item, context) != AdmissionResult.DENY;
    }

    public @Nonnull ItemResult consume(
            @Nullable ItemStack item, int amount, boolean replaceConsumables, @Nonnull ConsumeContext context) {
        VirtualItemHandler handler = resolveHandler(item);
        if (handler == null) {
            return ItemResult.notHandled();
        }

        return handler.consume(item, amount, replaceConsumables, context);
    }

    public @Nonnull ItemResult getRemainder(@Nullable ItemStack item, @Nonnull RemainderContext context) {
        VirtualItemHandler handler = resolveHandler(item);
        if (handler == null) {
            return ItemResult.notHandled();
        }

        return handler.getRemainder(item, context);
    }

    public boolean fits(
            @Nonnull Inventory inventory, @Nonnull ItemStack item, @Nonnull InventoryContext context, int... slots) {
        // Fail closed on stale or malformed addon slot layouts before Dough reads
        // a physical slot. A smaller legacy menu must never look like available space.
        if (!hasValidSlotSelection(inventory.getSize(), slots)) {
            return false;
        }

        // Dough's fast-path capacity check assumes one source stack can occupy
        // one physical slot. An oversized output (e.g. 65 cobblestone) must be
        // simulated across actual slots instead of treating a single empty slot
        // as sufficient, even when addons list that same slot more than once.
        if (!hasVirtualItemsInSlots(inventory, slots)
                && !isVirtualItem(item)
                && SlimefunItem.getByItem(item) == null
                && item.getAmount() <= Math.min(item.getMaxStackSize(), inventory.getMaxStackSize())) {
            if (slots.length == 0) {
                return InvUtils.fits(inventory, item);
            }

            return InvUtils.fits(inventory, ItemStackWrapper.wrap(item), slots);
        }

        ItemStack[] contents = Arrays.stream(inventory.getContents())
                .map(stack -> stack == null ? null : stack.clone())
                .toArray(ItemStack[]::new);
        return insertIntoSnapshot(contents, inventory.getMaxStackSize(), item, context, slots) <= 0;
    }

    public boolean fitAll(
            @Nonnull Inventory inventory, @Nonnull ItemStack[] items, @Nonnull InventoryContext context, int... slots) {
        // Both the vanilla Dough path and the virtual-item snapshot must reject
        // an invalid configured slot, without consuming outputs or modifying state.
        if (!hasValidSlotSelection(inventory.getSize(), slots)) {
            return false;
        }

        // Recipe-output preflight must model actual physical capacity when
        // addons repeat a slot or supply an oversized combined output. Dough's
        // vanilla fast path is retained for ordinary distinct-slot recipes.
        boolean requiresSnapshot = hasRepeatedSlots(slots);
        for (ItemStack item : items) {
            if (item != null
                    && (isVirtualItem(item)
                            || (!item.getType().isAir()
                                    && item.getAmount()
                                            > Math.min(item.getMaxStackSize(), inventory.getMaxStackSize())))) {
                requiresSnapshot = true;
                break;
            }
        }

        if (!requiresSnapshot) {
            requiresSnapshot = hasVirtualItemsInSlots(inventory, slots);
        }

        if (!requiresSnapshot) {
            return InvUtils.fitAll(inventory, items, slots);
        }

        ItemStack[] contents = Arrays.stream(inventory.getContents())
                .map(stack -> stack == null ? null : stack.clone())
                .toArray(ItemStack[]::new);

        for (ItemStack item : items) {
            if (item == null || item.getType().isAir()) {
                continue;
            }

            if (insertIntoSnapshot(contents, inventory.getMaxStackSize(), item, context, slots) > 0) {
                return false;
            }
        }

        return true;
    }

    public @Nullable ItemStack addItem(
            @Nonnull Inventory inventory, @Nonnull ItemStack item, @Nonnull InventoryContext context, int... slots) {
        Validate.notNull(item, "The item cannot be null");

        // Match fits/fitAll: a malformed output slot list must not partially
        // insert items into valid slots while silently ignoring invalid ones.
        // Return the entire remainder without mutating either the input or inventory.
        if (!hasValidSlotSelection(inventory.getSize(), slots)) {
            return item.clone();
        }

        boolean hasVirtualItems = hasVirtualItemsInSlots(inventory, slots);

        if (!hasVirtualItems && !isVirtualItem(item) && SlimefunItem.getByItem(item) == null && slots.length == 0) {
            Map<Integer, ItemStack> leftovers = inventory.addItem(item.clone());
            if (leftovers.isEmpty()) {
                return null;
            }

            return leftovers.values().iterator().next();
        }

        if (!hasVirtualItems && !isVirtualItem(item) && SlimefunItem.getByItem(item) == null && slots.length > 0) {
            return addItemDirectly(inventory, item, context, slots);
        }

        ItemStack[] contents = Arrays.stream(inventory.getContents())
                .map(stack -> stack == null ? null : stack.clone())
                .toArray(ItemStack[]::new);
        int amountLeft = insertIntoSnapshot(contents, inventory.getMaxStackSize(), item, context, slots);
        inventory.setContents(contents);

        if (amountLeft <= 0) {
            return null;
        }

        ItemStack remainder = item.clone();
        remainder.setAmount(amountLeft);
        return remainder;
    }

    private @Nullable ItemStack addItemDirectly(
            @Nonnull Inventory inventory, @Nonnull ItemStack item, @Nonnull InventoryContext context, int... slots) {
        int amountLeft = item.getAmount();
        int inventoryMaxStackSize = inventory.getMaxStackSize();

        for (int slot : slots) {
            if (slot < 0 || slot >= inventory.getSize()) {
                continue;
            }

            ItemStack itemInSlot = inventory.getItem(slot);

            if (itemInSlot == null || itemInSlot.getType().isAir()) {
                int maxStackSize = Math.min(item.getMaxStackSize(), inventoryMaxStackSize);
                int movedAmount = Math.min(amountLeft, maxStackSize);

                ItemStack inserted = item.clone();
                inserted.setAmount(movedAmount);
                inventory.setItem(slot, inserted);
                amountLeft -= movedAmount;
            } else if (itemInSlot.isSimilar(item)) {
                int maxStackSize = Math.min(itemInSlot.getMaxStackSize(), inventoryMaxStackSize);
                int freeSpace = Math.max(0, maxStackSize - itemInSlot.getAmount());

                if (freeSpace <= 0) {
                    continue;
                }

                int movedAmount = Math.min(amountLeft, freeSpace);
                itemInSlot.setAmount(itemInSlot.getAmount() + movedAmount);
                amountLeft -= movedAmount;
            }

            if (amountLeft <= 0) {
                return null;
            }
        }

        if (amountLeft <= 0) {
            return null;
        }

        ItemStack remainder = item.clone();
        remainder.setAmount(amountLeft);
        return remainder;
    }

    private int insertIntoSnapshot(
            @Nonnull ItemStack[] contents,
            int inventoryMaxStackSize,
            @Nonnull ItemStack item,
            @Nonnull InventoryContext context,
            int... slots) {
        int amountLeft = item.getAmount();
        int[] resolvedSlots = resolveSlots(contents.length, slots);

        for (int slot : resolvedSlots) {
            ItemStack itemInSlot = contents[slot];

            if (itemInSlot == null || itemInSlot.getType().isAir()) {
                if (!canInsertIntoEmptySlot(item, context)) {
                    continue;
                }

                int maxStackSize =
                        Math.min(getMaxStackSize(item, context, item.getMaxStackSize()), inventoryMaxStackSize);
                int movedAmount = Math.min(amountLeft, maxStackSize);

                ItemStack inserted = item.clone();
                inserted.setAmount(movedAmount);
                contents[slot] = inserted;
                amountLeft -= movedAmount;
            } else if (canMerge(itemInSlot, item)) {
                int maxStackSize = Math.min(
                        getMaxStackSize(itemInSlot, context, itemInSlot.getMaxStackSize()), inventoryMaxStackSize);
                int freeSpace = maxStackSize - itemInSlot.getAmount();

                if (freeSpace <= 0) {
                    continue;
                }

                int movedAmount = Math.min(amountLeft, freeSpace);
                itemInSlot.setAmount(itemInSlot.getAmount() + movedAmount);
                amountLeft -= movedAmount;
            }

            if (amountLeft <= 0) {
                return 0;
            }
        }

        return amountLeft;
    }

    private boolean canMerge(@Nonnull ItemStack existing, @Nonnull ItemStack incoming) {
        ComparisonResult comparison = matches(existing, incoming, MatchContext.STACK_MERGE);
        if (comparison == ComparisonResult.MATCH) {
            return true;
        }

        if (comparison == ComparisonResult.NO_MATCH) {
            return false;
        }

        ItemStackWrapper wrapper = ItemStackWrapper.wrap(incoming);
        if (SlimefunItem.getByItem(existing) != null || SlimefunItem.getByItem(incoming) != null) {
            return SlimefunUtils.isItemSimilarWithoutVirtualItems(existing, wrapper, true, false);
        }

        return ItemUtils.canStack(wrapper, existing);
    }

    private boolean hasVirtualItemsInSlots(@Nonnull Inventory inventory, int... slots) {
        for (int slot : resolveSlots(inventory.getSize(), slots)) {
            if (resolveHandler(inventory.getItem(slot)) != null) {
                return true;
            }
        }

        return false;
    }

    /**
     * Resolve the {@link VirtualItemHandler} for the given stack by looking up the
     * {@link SlimefunItem} and checking whether it has a registered handler that claims the stack.
     *
     * @param item
     *            The stack to inspect
     *
     * @return The handler, or {@code null} if none claims this stack
     */
    private @Nullable VirtualItemHandler resolveHandler(@Nullable ItemStack item) {
        if (item == null || item.getType().isAir()) {
            return null;
        }

        SlimefunItem sfItem = SlimefunItem.getByItem(item);
        if (sfItem == null) {
            return null;
        }

        Optional<ItemHandler> opt = sfItem.getHandlers().stream()
                .filter(h -> h instanceof VirtualItemHandler)
                .findFirst();
        if (opt.isEmpty()) {
            return null;
        }

        VirtualItemHandler handler = (VirtualItemHandler) opt.get();
        if (!handler.isVirtualItem(item)) {
            return null;
        }

        return handler;
    }

    /**
     * Repeated output slots describe only one physical capacity. The common
     * 18/54-slot layouts are checked without allocating collections.
     */
    private static boolean hasRepeatedSlots(int[] slots) {
        long seen = 0L;
        for (int i = 0; i < slots.length; i++) {
            int slot = slots[i];
            if (slot >= Long.SIZE) {
                for (int earlier = 0; earlier < i; earlier++) {
                    if (slots[earlier] == slot) {
                        return true;
                    }
                }
            } else {
                // Negative selectors are rejected by hasValidSlotSelection.
                long bit = 1L << slot;
                if ((seen & bit) != 0L) {
                    return true;
                }
                seen |= bit;
            }
        }
        return false;
    }

    /**
     * An empty selection means all slots, as in Dough. An explicit selection must
     * be valid in its entirety: silently skipping a bad output slot could allow a
     * machine to complete without enough real physical output capacity.
     */
    static boolean hasValidSlotSelection(int inventorySize, int... slots) {
        if (inventorySize < 0) {
            return false;
        }
        for (int slot : slots) {
            if (slot < 0 || slot >= inventorySize) {
                return false;
            }
        }
        return true;
    }

    private int[] resolveSlots(int inventorySize, int... slots) {
        if (slots.length > 0) {
            return Arrays.stream(slots)
                    .filter(slot -> slot >= 0 && slot < inventorySize)
                    .toArray();
        }

        int[] resolvedSlots = new int[inventorySize];
        for (int slot = 0; slot < inventorySize; slot++) {
            resolvedSlots[slot] = slot;
        }

        return resolvedSlots;
    }
}
