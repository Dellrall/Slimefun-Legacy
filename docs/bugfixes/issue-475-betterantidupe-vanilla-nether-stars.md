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

For a vanilla recipe template that has no metadata, the comparator now
accepts a candidate only if:

1. It has **exactly one** PDC key, named `antidupepro:adp_owner`.
2. After removing that key **on a clone of ItemMeta**, Bukkit's item
   factory regards the remaining metadata as empty/default.
3. Material and required stack amount still satisfy the original recipe.

This is not a general-purpose stripping of foreign PDC or Slimefun IDs.
Renames, custom model data, enchantments, lore, additional PDC keys (even
other anti-dupe keys) and Slimefun-specific IDs continue to block plain
vanilla matching. The live input item and its anti-dupe ownership metadata
are not changed by recipe **comparison**; normal recipe processing still
uses the machine's existing consumption logic.

## Required validation

The new MockBukkit tests cover ordinary Nether Stars before/after marking,
multiple PDC value types, stack amounts, material identity, metadata
preservation, marked custom items, extra keys, names, lore, enchantments
and custom models. Verify the exact-head Java 21 core build, Paper/Purpur
1.21.11 and 26.3 API/runtime checks, then run the reported live reproduction
with a genuinely BetterAntiDupe-marked Nether Star and both Heated Pressure
Chamber tiers. Make sure the Nether Star's anti-dupe marker remains intact
until the machine's normal consumption stage.

This code does not disable BetterAntiDupe, remove ownership markers from
inventories, change stored items, alter the existing recipe or change
Geyser/Bedrock behavior.
