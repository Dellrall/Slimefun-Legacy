# Folia 26.3 addon admission audit

**Status: descriptor admission audit only. Not addon runtime certification.**

Core Slimefun Legacy has a separate Folia 26.3 experimental readiness lane. The
canonical addon ZIP requires its own admission work because Folia plugins must opt in
explicitly and each addon can still contain region-unsafe behavior even when its
descriptor allows loading.

An initial offline audit of the exact 45-addon r137 selection found:

- **12** addon JARs declaring `folia-supported: true`;
- **0** declaring `folia-supported: false`;
- **33** with no `folia-supported` declaration.

A missing declaration means **unadmitted/unknown for this audit**, not "broken".
Likewise, `folia-supported: true` means only that the plugin descriptor opts into
Folia loading; it does not prove gameplay or concurrency safety.

## Initially declared true

- `wickidcow/SF_DracFun2`
- `wickidcow/SF_BetterFarming`
- `wickidcow/SF_CrystamaeHistoria`
- `wickidcow/SF_GeneticChickEngineering`
- `wickidcow/SF_HotbarPets`
- `wickidcow/SF_IDreamOfEasy`
- `wickidcow/SF_LuckyBlocks`
- `wickidcow/SF_MobCapturer`
- `wickidcow/SF_SMG`
- `wickidcow/SF_SlimeHUD`
- `wickidcow/SF_SlimyTreeTaps`
- `wickidcow/SF_SoulJars`

The exact-head CI audit is authoritative for future changes and publishes a JSON
artifact containing repository, commit, JAR, descriptor, digest and admission state
for every manifest-listed addon.

The audit parses YAML and requires an explicit top-level Boolean `true` or `false`.
Nested keys and description text do not opt a plugin in. Invalid declarations,
ambiguous duplicate top-level keys, YAML merge keys, duplicate ZIP members and
manifest/JAR digest mismatches fail the audit. A Paper descriptor takes precedence
when a JAR also contains a Bukkit fallback descriptor.

CI verifies the workflow event, PR head, actual tested checkout, exact maintained
source pins and every JAR hash through the shared candidate downloader. The source
receipt is retained alongside the admission report. Manual audits require a successful
push bundle for the same checkout; they cannot substitute a PR merge or release ZIP.
The existing 80-minute bundle wait is retained without relaxing identity checks.

## What should happen next

Admission should proceed in evidence-backed groups rather than bulk-adding the
descriptor flag:

1. **Already declared true:** run Folia 26.3 startup and representative callback tests;
   keep the flag only when region ownership rules remain satisfied.
2. **Storage/network addons:** Networks, InfinityExpansion2, BetterChests,
   FluffyMachines, DankTech2 and FinalTECH require explicit region-boundary review
   before opt-in. Cross-region transfers must remain refused or correctly scheduled;
   startup alone is insufficient.
3. **Menu/guide/HUD addons:** JEG, SlimeHUD and similar player-facing addons require
   entity/player scheduler review plus real menu/callback tests.
4. **Machines and mob/entity addons:** audit scheduler ownership for block ticks,
   spawning, teleports, entity mutation and delayed callbacks before descriptor opt-in.
5. Rebuild the exact canonical bundle and run a Folia 26.3 addon runtime lane after
   each reviewed batch.

## Promotion boundary

Do not call the 45-addon bundle "Folia 26.3 compatible" until every required addon is
both admitted and covered by appropriate runtime evidence. A server owner must still
test their complete third-party plugin set and a copied world before production use.
