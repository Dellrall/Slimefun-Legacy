# Folia 26.3 addon admission audit

**Status: descriptor admission plus declared-addon startup runtime admission. Not gameplay certification.**

Core Slimefun Legacy has a separate Folia 26.3 experimental readiness lane. The
canonical addon ZIP requires its own admission work because Folia plugins must opt in
explicitly and each addon can still contain region-unsafe behavior even when its
descriptor allows loading.

An initial offline audit of the exact 45-addon r137 selection found:

- **12** addon JARs declaring `folia-supported: true`;
- **0** declaring `folia-supported: false`;
- **33** with no `folia-supported` declaration.

A missing declaration means **unadmitted/unknown for this audit**, not "broken".
Likewise, `folia-supported: true` first means only that the plugin descriptor opts into
Folia loading. CI now takes the explicitly declared subset through a separate two-boot
Folia 26.3 startup lane, but even a successful startup does not prove gameplay or
cross-region concurrency safety.

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

## Declared-addon runtime startup admission

The same exact-source admission workflow now derives a runtime subset directly from the
audited canonical bundle. It rechecks the bundle SHA-256, every selected addon JAR
digest, descriptor name, explicit Boolean Folia declaration and hard dependencies
before copying any JAR into the disposable server.

Only addons whose audited descriptor contains top-level `folia-supported: true` are
selected. Hard dependencies must be Slimefun or another selected addon; soft
dependencies are intentionally optional for this startup lane.

A dependent job then builds Slimefun Legacy from the exact same checkout and boots the
selected addon JARs twice on official Folia 26.3. Both boots must:

- reach normal server startup;
- enable Slimefun and every selected addon by its descriptor plugin name;
- keep every selected addon enabled until normal server shutdown starts;
- contain no plugin enable/linkage failure markers;
- run the normal Slimefun upgrade-readiness check without a BLOCKED result;
- shut down normally, with the second boot observing the prior clean Slimefun shutdown.

The expected plugin/JAR pairs must match the selection exactly. The installed core
and addon bytes are checked before each boot and after the final shutdown, rejecting
missing, substituted or extra JARs. The installed-plugin receipt, selected JAR list,
source commits, per-JAR hashes, console logs, tested Folia build and two-boot result
are retained as CI artifacts. This is stronger than descriptor-only
admission, but remains **startup evidence only**. It does not exercise each addon's
menus, machines, delayed callbacks, teleports, entities, storage paths or cross-region
operations.


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

1. **Already declared true:** keep the automated Folia 26.3 two-boot startup admission green,
   then add representative callback/gameplay tests for region-sensitive features; keep the
   flag only when region ownership rules remain satisfied.
2. **Storage/network addons:** Networks, InfinityExpansion2, BetterChests,
   FluffyMachines, DankTech2 and FinalTECH require explicit region-boundary review
   before opt-in. Cross-region transfers must remain refused or correctly scheduled;
   startup alone is insufficient.
3. **Menu/guide/HUD addons:** JEG, SlimeHUD and similar player-facing addons require
   entity/player scheduler review plus real menu/callback tests.
4. **Machines and mob/entity addons:** audit scheduler ownership for block ticks,
   spawning, teleports, entity mutation and delayed callbacks before descriptor opt-in.
5. Rebuild the exact canonical bundle after each reviewed batch; the declared-addon
   Folia startup lane will consume that exact bundle automatically. Add deeper runtime
   probes for each promoted feature group before claiming gameplay support.

## Promotion boundary

Do not call the 45-addon bundle "Folia 26.3 compatible" until every required addon is
both admitted and covered by appropriate runtime evidence. A server owner must still
test their complete third-party plugin set and a copied world before production use.
