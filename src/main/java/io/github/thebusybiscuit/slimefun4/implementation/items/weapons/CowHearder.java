package io.github.thebusybiscuit.slimefun4.implementation.items.weapons;

import io.github.thebusybiscuit.slimefun4.api.items.ItemGroup;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItem;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItemStack;
import io.github.thebusybiscuit.slimefun4.api.recipes.RecipeType;
import io.github.thebusybiscuit.slimefun4.core.attributes.NotConfigurable;
import io.github.thebusybiscuit.slimefun4.implementation.Slimefun;
import org.bukkit.Material;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

/**
 * An uncraftable, guide-hidden operator tool. Its effects apply only while an operator
 * actually holds the registered Slimefun item in their main hand.
 */
public final class CowHearder extends SlimefunItem implements Listener, NotConfigurable {

    public static final String ID = "COW_HEARDER";

    // Finite, well below double overflow, but far above normal player and boss health.
    private static final double STRIKE_DAMAGE = 1_000_000_000_000.0D;

    private CowHearder(ItemGroup group) {
        super(
                group,
                new SlimefunItemStack(
                        ID,
                        Material.NETHERITE_SWORD,
                        "&2&lThe Cow Hearder",
                        "&8An implement of absolute authority",
                        "",
                        "&6One strike. Overwhelming damage.",
                        "&bImmune to incoming damage while held.",
                        "&8Operator use only"),
                RecipeType.NULL,
                new ItemStack[9]);

        setHidden(true);

        ItemMeta meta = getItem().getItemMeta();
        meta.setUnbreakable(true);
        meta.setMaxStackSize(1);
        meta.addEnchant(Enchantment.SHARPNESS, 255, true);
        meta.addEnchant(Enchantment.SMITE, 255, true);
        meta.addEnchant(Enchantment.BANE_OF_ARTHROPODS, 255, true);
        meta.addEnchant(Enchantment.SWEEPING_EDGE, 255, true);
        meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_UNBREAKABLE, ItemFlag.HIDE_ENCHANTS);
        getItem().setItemMeta(meta);
    }

    public static void register(Slimefun plugin, ItemGroup group) {
        CowHearder item = new CowHearder(group);
        item.register(plugin);
        plugin.getServer().getPluginManager().registerEvents(item, plugin);
    }

    /**
     * Give permission is independent of ordinary Slimefun cheat-item permission.
     * The console may grant it only to an operator, and the amount is always one.
     */
    public static boolean mayGive(boolean isPrivilegedSender, boolean isOperatorRecipient, int amount) {
        return isPrivilegedSender && isOperatorRecipient && amount == 1;
    }

    private boolean isActive(Player player) {
        return player.isOp() && SlimefunItem.getByItem(player.getInventory().getItemInMainHand()) == this;
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onStrike(EntityDamageByEntityEvent event) {
        if (event.getDamager() instanceof Player player
                && event.getEntity() instanceof LivingEntity
                && isActive(player)) {
            // Respect cancelled attacks (PvP flags, regions, and other plugins).
            event.setDamage(STRIKE_DAMAGE);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onProtected(EntityDamageEvent event) {
        if (event.getEntity() instanceof Player player && isActive(player)) {
            // Covers fall, fire, explosions, projectiles, drowning, void, magic, etc.
            // A plugin that sets health directly does not emit this event.
            event.setCancelled(true);
        }
    }
}
