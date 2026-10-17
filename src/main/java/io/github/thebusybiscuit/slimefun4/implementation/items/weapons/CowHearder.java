package io.github.thebusybiscuit.slimefun4.implementation.items.weapons;

import io.github.thebusybiscuit.slimefun4.api.items.ItemGroup;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItem;
import io.github.thebusybiscuit.slimefun4.api.items.SlimefunItemStack;
import io.github.thebusybiscuit.slimefun4.api.recipes.RecipeType;
import io.github.thebusybiscuit.slimefun4.core.attributes.NotConfigurable;
import io.github.thebusybiscuit.slimefun4.implementation.Slimefun;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.bukkit.GameMode;
import org.bukkit.GameRules;
import org.bukkit.Material;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

/**
 * An uncraftable, guide-hidden operator tool. Effects apply only to the registered
 * Slimefun item while an operator holds it in their main hand.
 */
public final class CowHearder extends SlimefunItem implements Listener, NotConfigurable {

    public static final String ID = "COW_HEARDER";

    // Keep normal player strikes comfortably lethal without overflowing other plugins' hit statistics.
    private static final double MIN_STRIKE_DAMAGE = 16_384.0D;
    private static final double MAX_STRIKE_DAMAGE = 1_000_000_000_000.0D;
    private static final double HEALTH_MULTIPLIER = 1_024.0D;

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
                        "&bImmune to normal damage while held.",
                        "&7Sneak + right-click to inspect PvP.",
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

    /**
     * Armor, absorption and MythicMobs health can exceed vanilla player health.
     * Scale to the target without the trillion-point hit that can overflow third-party counters.
     */
    static double strikeDamage(double health, double absorption) {
        double safeHealth = Double.isFinite(health) ? Math.max(0.0D, health) : MAX_STRIKE_DAMAGE;
        double safeAbsorption = Double.isFinite(absorption) ? Math.max(0.0D, absorption) : MAX_STRIKE_DAMAGE;
        return Math.min(
                MAX_STRIKE_DAMAGE,
                Math.max(MIN_STRIKE_DAMAGE, (safeHealth + safeAbsorption) * HEALTH_MULTIPLIER));
    }

    static boolean shouldBlockDamage(boolean authorizedWielder, boolean incomingCowHearderStrike) {
        return authorizedWielder && !incomingCowHearderStrike;
    }

    private boolean isActive(Player player) {
        return player.isOp() && SlimefunItem.getByItem(player.getInventory().getItemInMainHand()) == this;
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onStrike(EntityDamageByEntityEvent event) {
        if (event.getDamager() instanceof Player player
                && event.getEntity() instanceof LivingEntity target
                && isActive(player)) {
            // Respect attacks cancelled by PvP/region plugins. Do not set health directly.
            event.setDamage(strikeDamage(target.getHealth(), target.getAbsorptionAmount()));
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onProtected(EntityDamageEvent event) {
        if (!(event.getEntity() instanceof Player victim)) {
            return;
        }

        boolean incomingCowHearderStrike = event instanceof EntityDamageByEntityEvent hit
                && hit.getDamager() instanceof Player attacker
                && attacker != victim
                && isActive(attacker);

        // Two operators with these weapons may fight each other. Other damage cannot hurt the wielder.
        if (shouldBlockDamage(isActive(victim), incomingCowHearderStrike)) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onStrikeResult(EntityDamageByEntityEvent event) {
        if (!(event.getDamager() instanceof Player attacker)
                || !(event.getEntity() instanceof LivingEntity)
                || !isActive(attacker)) {
            return;
        }

        if (event.getEntity() instanceof Player victim
                && (victim.getGameMode() == GameMode.CREATIVE || victim.getGameMode() == GameMode.SPECTATOR)) {
            attacker.sendActionBar(Component.text(
                    "Cow Hearder: target is in Creative or Spectator mode.", NamedTextColor.YELLOW));
        } else if (event.isCancelled()) {
            boolean pvpDisabled = event.getEntity() instanceof Player
                    && Boolean.FALSE.equals(attacker.getWorld().getGameRuleValue(GameRules.PVP));
            attacker.sendActionBar(Component.text(
                    pvpDisabled
                            ? "Cow Hearder: PvP is disabled in this world."
                            : "Cow Hearder: hit cancelled by another plugin or area protection.",
                    NamedTextColor.RED));
        } else if (event.getFinalDamage() <= 0.0D) {
            attacker.sendActionBar(Component.text(
                    "Cow Hearder: damage was reduced to zero by a defensive effect.",
                    NamedTextColor.YELLOW));
        }
    }

    @EventHandler
    public void onInspect(PlayerInteractEvent event) {
        if (event.getHand() != EquipmentSlot.HAND
                || !event.getAction().isRightClick()
                || !event.getPlayer().isSneaking()
                || !isActive(event.getPlayer())) {
            return;
        }

        boolean pvpEnabled = Boolean.TRUE.equals(event.getPlayer().getWorld().getGameRuleValue(GameRules.PVP));
        event.getPlayer()
                .sendMessage(Component.text(
                        "Cow Hearder active. World PvP gamerule: " + (pvpEnabled ? "ON" : "OFF")
                                + ". Protected regions and other plugins can still cancel hits.",
                        pvpEnabled ? NamedTextColor.GREEN : NamedTextColor.YELLOW));
    }
}
