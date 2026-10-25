package io.github.thebusybiscuit.slimefun4.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import net.kyori.adventure.text.Component;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;

/** Regression for issue #475: BetterAntiDupe-owned Nether Stars are still vanilla recipe inputs. */
class TestAntiDupeVanillaRecipeMatching {

    private static final NamespacedKey OWNER = new NamespacedKey("antidupepro", "adp_owner");
    private static final NamespacedKey FOREIGN_ITEM_ID = new NamespacedKey("some_plugin", "special_item");
    private static final NamespacedKey SLIMEFUN_ITEM_ID = new NamespacedKey("slimefun", "id");

    @BeforeEach
    void startServer() {
        MockBukkit.mock();
    }

    @AfterEach
    void stopServer() {
        MockBukkit.unmock();
    }

    @Test
    void plainVanillaStarMatchesBeforeAndAfterBetterAntiDupeMarksIt() {
        ItemStack candidate = new ItemStack(Material.NETHER_STAR, 3);
        ItemStack recipeStar = new ItemStack(Material.NETHER_STAR);

        assertTrue(matches(candidate, recipeStar));

        ItemMeta meta = candidate.getItemMeta();
        meta.getPersistentDataContainer().set(OWNER, PersistentDataType.STRING, "player-owner-uuid");
        candidate.setItemMeta(meta);

        assertTrue(matches(candidate, recipeStar),
                "One invisible BetterAntiDupe owner tag must not block a Heated Pressure Chamber recipe");
        assertEquals("player-owner-uuid",
                candidate.getItemMeta().getPersistentDataContainer().get(OWNER, PersistentDataType.STRING),
                "Recipe comparison must not remove, rewrite or mutate the anti-dupe ownership marker");
        assertEquals(3, candidate.getAmount(), "Recipe comparison must not consume the input");
    }

    @Test
    void anyPersistentValueTypeForTheSameOwnerKeyIsOnlyComparisonMetadata() {
        ItemStack candidate = new ItemStack(Material.NETHER_STAR);
        ItemMeta meta = candidate.getItemMeta();
        meta.getPersistentDataContainer().set(OWNER, PersistentDataType.INTEGER, 42);
        candidate.setItemMeta(meta);

        assertTrue(matches(candidate, new ItemStack(Material.NETHER_STAR)));
        assertEquals(42,
                candidate.getItemMeta().getPersistentDataContainer().get(OWNER, PersistentDataType.INTEGER));
    }

    @Test
    void normalVanillaMatchingConstraintsStillApply() {
        ItemStack candidate = markedStar();
        assertFalse(matches(candidate, new ItemStack(Material.DIAMOND)));
        assertFalse(matches(candidate, new ItemStack(Material.NETHER_STAR, 2)));
        assertTrue(matches(candidate, new ItemStack(Material.NETHER_STAR)));
    }

    @Test
    void ownerMarkPlusAnotherForeignOrSlimefunItemIdIsNotAPlainVanillaStar() {
        ItemStack candidate = markedStar();
        ItemMeta meta = candidate.getItemMeta();
        meta.getPersistentDataContainer().set(FOREIGN_ITEM_ID, PersistentDataType.STRING, "custom");
        candidate.setItemMeta(meta);
        assertFalse(matches(candidate, new ItemStack(Material.NETHER_STAR)));

        meta.getPersistentDataContainer().remove(FOREIGN_ITEM_ID);
        meta.getPersistentDataContainer().set(SLIMEFUN_ITEM_ID, PersistentDataType.STRING, "BLISTERING_INGOT_2");
        candidate.setItemMeta(meta);
        assertFalse(matches(candidate, new ItemStack(Material.NETHER_STAR)));
    }

    @Test
    void arbitraryForeignPdcMarkersAreNotIgnored() {
        ItemStack candidate = new ItemStack(Material.NETHER_STAR);
        ItemMeta meta = candidate.getItemMeta();
        meta.getPersistentDataContainer().set(FOREIGN_ITEM_ID, PersistentDataType.STRING, "custom");
        candidate.setItemMeta(meta);
        assertFalse(matches(candidate, new ItemStack(Material.NETHER_STAR)));
    }

    @Test
    void namesLoreEnchantmentsAndCustomModelDataRemainSignificant() {
        ItemStack renamed = markedStar();
        ItemMeta renamedMeta = renamed.getItemMeta();
        renamedMeta.displayName(Component.text("Special Nether Star"));
        renamed.setItemMeta(renamedMeta);
        assertFalse(matches(renamed, new ItemStack(Material.NETHER_STAR)));

        ItemStack withLore = markedStar();
        ItemMeta loreMeta = withLore.getItemMeta();
        loreMeta.lore(java.util.List.of(Component.text("Different ingredient")));
        withLore.setItemMeta(loreMeta);
        assertFalse(matches(withLore, new ItemStack(Material.NETHER_STAR)));

        ItemStack enchanted = markedStar();
        ItemMeta enchantedMeta = enchanted.getItemMeta();
        enchantedMeta.addEnchant(Enchantment.UNBREAKING, 1, true);
        enchanted.setItemMeta(enchantedMeta);
        assertFalse(matches(enchanted, new ItemStack(Material.NETHER_STAR)));

        ItemStack modeled = markedStar();
        ItemMeta modelMeta = modeled.getItemMeta();
        modelMeta.setCustomModelData(321);
        modeled.setItemMeta(modelMeta);
        assertFalse(matches(modeled, new ItemStack(Material.NETHER_STAR)));
    }

    private static ItemStack markedStar() {
        ItemStack star = new ItemStack(Material.NETHER_STAR);
        ItemMeta meta = star.getItemMeta();
        meta.getPersistentDataContainer().set(OWNER, PersistentDataType.STRING, "owner");
        star.setItemMeta(meta);
        return star;
    }

    private static boolean matches(ItemStack candidate, ItemStack expectedVanillaRecipeIngredient) {
        return SlimefunUtils.isItemSimilarWithoutVirtualItems(
                candidate, expectedVanillaRecipeIngredient, true, true);
    }
}
