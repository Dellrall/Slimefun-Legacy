# Issue #475 — Heated Pressure Chamber and marked Nether Stars

**Status:** Development fix; Slimefun Legacy 4.1.78 remains unpublished.

## Reproduction and confirmed cause

Reporter [Dellrall](https://github.com/wickidcow/Slimefun-Legacy/issues/475)
found that BetterAntiDupe adds an invisible
`antidupepro:adp_owner` PersistentDataContainer marker to otherwise normal
`NETHER_STAR` items after pickup, when containers close, or on its periodic
maintenance pass.

The Heated Pressure Chamber's existing input recipe is:
`BLISTERING_INGOT_2` (66%) + one vanilla `NETHER_STAR` ->
`BLISTERING_INGOT_3`. The other Blistering Ingot recipe involving two
Slimefun item IDs can still work because it matches by item ID.

Slimefun's plain vanilla comparator previously rejected a vanilla recipe
input whenever the candidate had metadata and the recipe template did not.
The anti-dupe marker was sufficient to make a visually unmodified Nether
Star fail that branch. This explains why a fresh star could work immediately
after startup but the same item later failed; energy, chamber registration
and player-visible descriptions did not establish the problem.

## Safe fix

**Only** `ItemStackService.isSimilar(... MatchContext.RECIPE_INPUT ...)`
accepts a marked item when the recipe expects a *plain vanilla Nether Star*:

1. The candidate and plain recipe template are both `NETHER_STAR`, with
   the correct ingredient quantity.
2. The candidate has **exactly one** PDC key, `antidupepro:adp_owner`,
   and is not a `SlimefunItemStack`.
3. After removing the key **from cloned ItemMeta**, the remainder equals
   a freshly created default `NETHER_STAR` meta via Bukkit's ItemFactory.
4. Names, custom models, enchantments, lore and any additional PDC keys
   block the exception, even when a server's ItemFactory normalizes them.

**General SlimefunUtils comparisons, Cargo/Networks stack merging and
auto-crafter predicate comparisons remain strict.** Ignoring ownership
markers outside the recipe-input context could merge another player's
marked item with an unmarked stack and destroy anti-dupe provenance.
This change deliberately does not weaken those paths.

The live input and its anti-dupe marker are unchanged by recipe
comparison; normal processing still uses the machine's existing
consumption and item-persistence logic.

## Required validation

The new MockBukkit tests cover ordinary Nether Stars before/after marking,
multiple PDC value types, stack amounts, material identity, metadata
preservation, marked custom items, extra keys, names, lore, enchantments,
custom models, and strict general/Cargo/auto-crafter comparisons. Verify the exact-head Java 21 core build, Paper/Purpur
1.21.11 and 26.3 API/runtime checks, then run the reported live reproduction
with a genuinely BetterAntiDupe-marked Nether Star and both Heated Pressure
Chamber tiers. Make sure the Nether Star's anti-dupe marker remains intact
until the machine's normal consumption stage.

This code does not disable BetterAntiDupe, remove ownership markers from
inventories, change stored items, alter the existing recipe or change
Geyser/Bedrock behavior.
