package io.github.thebusybiscuit.slimefun4.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.xzavier0722.mc.plugin.slimefun4.storage.controller.InventoryReadTestPlugin;
import io.github.thebusybiscuit.slimefun4.api.items.virtual.VirtualItemHandler.MatchContext;
import io.github.thebusybiscuit.slimefun4.core.services.ItemStackService;
import io.github.thebusybiscuit.slimefun4.utils.itemstack.ItemStackWrapper;
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
    void plainVanillaStarMatchesBeforeAndAfterBetterAntiDupeMarksIt() {
        ItemStack recipeStar = plainVanilla(Material.NETHER_STAR);
        assertTrue(matches(plainVanilla(Material.NETHER_STAR, 3), recipeStar));

        // MockBukkit's ItemFactory treats even an empty recipe meta as present,
        // whereas real Paper treats the vanilla template as metadata-free.
        // Explicit fixtures exercise the actual native matcher branches.
        ItemStack candidate = metadataAwareStar(3);
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
    void aContainerRecipeInputMatchingAcceptsTheMarkedStarAsWell() {
        ItemStack marked = markedStar();
        ItemStack recipeStar = plainVanilla(Material.NETHER_STAR);

        // MockBukkit's ItemFactory has different empty-meta semantics
        // from CraftBukkit. Bootstrap the wrapper with a temporary name
        // so its hasItemMeta bit is true, then remove that test-only name.
        // The plain recipe template fixture reports no metadata.
        ItemMeta setup = marked.getItemMeta();
        setup.displayName(Component.text("test-only metadata bootstrap"));
        marked.setItemMeta(setup);
        ItemStackWrapper wrapped = ItemStackWrapper.wrap(marked);
        assertTrue(wrapped.hasItemMeta(), "Fixture must traverse the metadata-aware recipe branch");
        wrapped.getItemMeta().displayName(null);

        // This is the exact ItemStackService route used by
        // AContainer#findNextRecipe, including its immutable ItemStackWrapper.
        assertTrue(new ItemStackService().isSimilar(
                wrapped, recipeStar, MatchContext.RECIPE_INPUT, true, true));

        wrapped.getItemMeta().getPersistentDataContainer().set(
                FOREIGN_ITEM_ID, PersistentDataType.STRING, "other-item");
        assertFalse(new ItemStackService().isSimilar(
                wrapped, recipeStar, MatchContext.RECIPE_INPUT, true, true));
    }

    @Test
    void anyPersistentValueTypeForTheSameOwnerKeyIsOnlyComparisonMetadata() {
        ItemStack candidate = metadataAwareStar(1);
        ItemMeta meta = candidate.getItemMeta();
        meta.getPersistentDataContainer().set(OWNER, PersistentDataType.INTEGER, 42);
        candidate.setItemMeta(meta);

        assertTrue(matches(candidate, plainVanilla(Material.NETHER_STAR)));
        assertEquals(42,
                candidate.getItemMeta().getPersistentDataContainer().get(OWNER, PersistentDataType.INTEGER));
    }

    @Test
    void normalVanillaMatchingConstraintsStillApply() {
        ItemStack candidate = markedStar();
        assertFalse(matches(candidate, plainVanilla(Material.DIAMOND)));
        assertFalse(matches(candidate, plainVanilla(Material.NETHER_STAR, 2)));
        assertTrue(matches(candidate, plainVanilla(Material.NETHER_STAR)));
    }

    @Test
    void ownerMarkPlusAnotherForeignOrSlimefunItemIdIsNotAPlainVanillaStar() {
        ItemStack candidate = markedStar();
        ItemMeta meta = candidate.getItemMeta();
        meta.getPersistentDataContainer().set(FOREIGN_ITEM_ID, PersistentDataType.STRING, "custom");
        candidate.setItemMeta(meta);
        assertFalse(matches(candidate, plainVanilla(Material.NETHER_STAR)));

        meta.getPersistentDataContainer().remove(FOREIGN_ITEM_ID);
        meta.getPersistentDataContainer().set(SLIMEFUN_ITEM_ID, PersistentDataType.STRING, "BLISTERING_INGOT_2");
        candidate.setItemMeta(meta);
        assertFalse(matches(candidate, plainVanilla(Material.NETHER_STAR)));
    }

    @Test
    void arbitraryForeignPdcMarkersAreNotIgnored() {
        ItemStack candidate = metadataAwareStar(1);
        ItemMeta meta = candidate.getItemMeta();
        meta.getPersistentDataContainer().set(FOREIGN_ITEM_ID, PersistentDataType.STRING, "custom");
        candidate.setItemMeta(meta);
        assertFalse(matches(candidate, plainVanilla(Material.NETHER_STAR)));
    }

    @Test
    void namesLoreEnchantmentsAndCustomModelDataRemainSignificant() {
        ItemStack renamed = markedStar();
        ItemMeta renamedMeta = renamed.getItemMeta();
        renamedMeta.displayName(Component.text("Special Nether Star"));
        renamed.setItemMeta(renamedMeta);
        assertFalse(matches(renamed, plainVanilla(Material.NETHER_STAR)));

        ItemStack withLore = markedStar();
        ItemMeta loreMeta = withLore.getItemMeta();
        loreMeta.lore(java.util.List.of(Component.text("Different ingredient")));
        withLore.setItemMeta(loreMeta);
        assertFalse(matches(withLore, plainVanilla(Material.NETHER_STAR)));

        ItemStack enchanted = markedStar();
        ItemMeta enchantedMeta = enchanted.getItemMeta();
        enchantedMeta.addEnchant(Enchantment.UNBREAKING, 1, true);
        enchanted.setItemMeta(enchantedMeta);
        assertFalse(matches(enchanted, plainVanilla(Material.NETHER_STAR)));

        ItemStack modeled = markedStar();
        ItemMeta modelMeta = modeled.getItemMeta();
        modelMeta.setCustomModelData(321);
        modeled.setItemMeta(modelMeta);
        assertFalse(matches(modeled, plainVanilla(Material.NETHER_STAR)));
    }

    private static ItemStack markedStar() {
        ItemStack star = metadataAwareStar(1);
        ItemMeta meta = star.getItemMeta();
        meta.getPersistentDataContainer().set(OWNER, PersistentDataType.STRING, "owner");
        star.setItemMeta(meta);
        return star;
    }

    /**
     * Force the metadata-aware candidate branch. MockBukkit's empty-item
     * semantics differ from CraftBukkit's, so the opposite side of the
     * comparison is an explicitly metadata-free vanilla recipe template.
     */
    private static ItemStack metadataAwareStar(int amount) {
        return new ItemStack(Material.NETHER_STAR, amount) {
            @Override
            public boolean hasItemMeta() {
                return true;
            }
        };
    }

    private static ItemStack plainVanilla(Material material) {
        return plainVanilla(material, 1);
    }

    /**
     * Vanilla recipe templates do not have custom ItemMeta. MockBukkit's
     * ItemFactoryMock.equals(meta, null) uses Object.equals and can treat
     * an empty nonnull ItemMeta as nonempty, so make that contract explicit.
     */
    private static ItemStack plainVanilla(Material material, int amount) {
        return new ItemStack(material, amount) {
            @Override
            public boolean hasItemMeta() {
                return false;
            }
        };
    }

    private static boolean matches(ItemStack candidate, ItemStack expectedVanillaRecipeIngredient) {
        return SlimefunUtils.isItemSimilarWithoutVirtualItems(
                candidate, expectedVanillaRecipeIngredient, true, true);
    }
}
