# Networks Expansion — core release integration checkpoint

Updated: 2026-10-22 (UTC). This file tracks the coordinated **Slimefun Legacy 4.1.76 / r145** candidate integration and the requested optional Bedrock download. Historical integration evidence is preserved below. The completed addon development remains recorded in [Networks' permanent checkpoint](https://github.com/wickidcow/SF_NetworksExp/blob/master/NETWORKS_EXPANSION_COMPLETION.md). Consult the current handoff and Git state before resuming; do not repeat accepted production repairs.

## Publication boundary

Core **4.1.76 remains unreleased and held for explicit maintainer approval** after the concrete candidate is verified. Continue integration, testing, review and merge without restarting the addon repairs. Do not publish a core tag/release or replace existing v4.1.75 assets during validation. `reproducible-release.yml` now defaults manual dispatch to `publish=false` and requires explicit `publish=true` plus successful runtime evidence for either publishing or normalizing assets.

## Current handoff — merged and verified complete candidate; publication held

PR [#417](https://github.com/wickidcow/Slimefun-Legacy/pull/417) merged normally
into `master` at **`9075ea852095b28543aaa1456bc2576778cb4c4d`**. Its tree is
**`061770ab05d8a25ac5cd4abb9dac141132c02898`**, identical to the reviewed PR head
`21ac88ca14f50d3441a3b0915a714d2d8a56810f`. The PR's 82 terminal checks comprise
**75 successes and seven intentional skips**, with no failure, cancellation or
pending check; all **10 applicable direct workflow families succeeded**. The
separate Purpur/Folia 26.3 PR workflow files were outside this change's path
conditions; the final-source native and Folia runs below provide fresh acceptance.
No workflow was disabled to obtain the result.

The release source remains **`9075ea852095b28543aaa1456bc2576778cb4c4d`** throughout
final validation. Core remains **4.1.76**, bundle **r145**, and all 45 addon source
pins and production Java remain unchanged by the Bedrock integration. **No further
version bump is needed.** The two externally replaced public Bedrock downloads
are provenance records rather than release acquisition dependencies. The complete
installation ZIP is committed in Git, verified by exact identity and copied
unchanged into the held four-asset release candidate.

This evidence-only checkpoint is stored on
`checkpoints/4.1.76-bedrock-verified-9075ea8`, based on
`9075ea852095b28543aaa1456bc2576778cb4c4d`; the release source remains
`9075ea852095b28543aaa1456bc2576778cb4c4d`. The checkpoint and
[final acceptance receipt](compatibility/release-acceptance/4.1.76-9075ea8.json)
preserve the completed verification without moving `master` or rebuilding the
release from a documentation-only commit. Keep the compiled source and runtime
evidence bound to `9075ea8`, not to the checkpoint commit. The tested intermediate
snapshot `debc3dec921ff27e7e35d4383861bca3e78a9649` and all older handoffs below
remain historical.

### Completed implementation


- Vendored `compatibility/bedrock/SFL_GEYSER_RP_experimental_v1.0.3_complete.zip`:
  **2,390,264 bytes**, SHA-256
  `60fb9fcfe19e7e5644ff7202fd83bcd2b73b9f7685f3a57797d73877153c014c`.
  It contains 28 files: all 23 mappings, two required main packs, a separate optional
  stat-icon pack, unchanged upstream `README.txt`, and new `INSTALL.md`.
- Preserved 21 base mapping files from the retained 0.0.2 archive and all six files
  from the current 1.0.3 overlay. All 27 supplied component files remain byte-identical;
  no inner pack, mapping identity, image or model was rewritten. The complete ZIP
  has 1,543 disjoint skull hashes (1,453 base plus 90 new), 507 Albion definitions,
  and no duplicate old main-pack versions. Deterministic outer serialization was
  repeated independently with identical bytes. The full component ledger and
  loader summary are committed in `compatibility/bedrock/complete-pack-provenance.json`.
- Schema 2 pins the repository archive and both original source identities as
  provenance. Removed historical assets are not required downloads. Release staging
  verifies the exact target tag, archive hash, size, safe unique paths, CRCs,
  mapping schemas, disjoint skull maps and nested JSON/material syntax before
  copying it. Both instruction files and the complete base mapping set are required.
- Cleanup preserves the exact current **overlay** only on origin `v4.1.75`, and the
  exact **complete ZIP** only on successor `v4.1.76`. Swapped roles, historical
  filenames, changed bytes and unreviewed future assets still stop before any DELETE.
  The complete ZIP does not replace or alter the public overlay during validation.
- README, release notes and installation guide state that the Bedrock download is
  optional and experimental; **Geyser, both main packs and all 23 JSON mappings are
  required**. The stat-icon font pack is separately optional. Upgrade instructions
  back up and replace only the two old main packs sharing the new packs' UUIDs.
  The public 1.0.3 overlay alone is explicitly unsuitable for a fresh installation.

### Local verification retained

- Archive verifier: **45/45 PASS normally and 45/45 with `python -O`**. The real
  complete ZIP passes with no origin metadata or network request; optional checking
  of retained current-overlay metadata also passes. Nested content: 2,758 files.
- Cleanup policy: **51/51 PASS normally and 51/51 with `python -O`**, after retained
  RED-before evidence against the previous policy. Normal and optimized policy
  preflights, plus the actual workflow shell exercised with live release metadata
  and a local `gh` stub, retain all four current public assets with **zero delete IDs**.
  Fresh before/after release metadata and actual overlay bytes are unchanged.
- Real release workflow shell: **7/7 PASS normally and 7/7 with `python -O`**,
  including unchanged-byte staging with **zero source API calls**, missing or
  changed archive rejection, exact four-asset normalization and explicit
  publication guards. All **26 release dispatch/evidence controls PASS**.
- Exact complete-ZIP runtime: **Geyser Standalone 2.12.0 build 1268**, source
  `d14f204635dceb37f2bfaf87cc3b733bc4f1e1eb`, Java 25.0.4.1. Both a fresh default
  installation and a separate run with optional stat icons loaded successfully,
  registered **1,543 custom skulls/blocks**, generated 1,543 skull textures and
  shut down normally (exit zero). All 28 candidate input files remained unchanged.
  Runtime receipt SHA-256:
  `7825e850e17081ed48dd7f045cd5fb4684dd853319e3b4dbd3a11af6786722e9`.
- Both runs retain **107 legacy texture-size deprecation warnings**. No Bedrock
  client or live Java backend connected. Rendering, hand/armor visuals, item
  interactions, production transport and embedded Geyser-Spigot/Folia behavior
  remain untested. The isolated transport configuration emitted its expected
  NetherNet migration notice; no pack/mapping load error was concealed. Actual
  1,543-block counts supersede the unchanged upstream README's unsupported count.
- The preceding isolated local Java clean build passed **941 tests / 162 suites,
  zero failures/errors and one existing external-database skip**, plus Spotless
  and the deprecation/removal gate. No production/build dependency changes followed
  that run. Its environment failures and final pass remain recorded below.
- Complete repository invariant suite: **PASS**; workflow YAML and all **14**
  embedded Bash scripts pass syntax checks. Independent bounded reviews of the
  verifier, cleanup, workflow and documentation are **CLEAR**. The first invariant
  attempt was blocked by sandbox-localhost socket restrictions in the HTTP fixture;
  the authorized rerun passed with no source or gate change. The completed hosted
  checks and final-source verification are recorded below. All 4c2bdf4e receipts
  in the historical sections still belong only to that prior merge.

### Hosted review and exact final-source verification

Every final-source result in this section binds source
`9075ea852095b28543aaa1456bc2576778cb4c4d`. PR artifacts and prior `4c2bdf4e`
artifacts are not substituted for the final canonical inputs.

| Gate | Actual result | Evidence |
| --- | --- | --- |
| PR #417 review and applicable CI | Normal merge; 82 terminal checks, 75 successful and seven intentional skips; all 10 direct workflow families successful | [PR #417](https://github.com/wickidcow/Slimefun-Legacy/pull/417), reviewed head `21ac88ca14f50d3441a3b0915a714d2d8a56810f` |
| Final main build | **PASS** | [39711112208](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39711112208), attempt 1 |
| Final canonical core and addon bundle | **48/48 jobs PASS**, including all 45 addon builds and packaging | [39711112456](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39711112456), attempt 1 |
| Existing public release preservation | **PASS; zero deleted assets**, all four current v4.1.75 assets retained | [39711112172](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39711112172), job `119602460091` |
| Native retirement and paired storage | **6/6 jobs PASS**; strict exact-release native pair accepted | [39711192917](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39711192917), attempt 1 |
| Folia admission and declared-addon startup | **PASS**; all 12 admitted original JAR identities reproduce exactly; GCE registers 64 chickens on each of two boots | [39711323021](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39711323021), attempt 1 |
| Automatic final full-stack follower | **7/7 jobs PASS**; four runtime lanes, eight stack boots with all 45 addons and 16 Black Market phase boots accepted | [39711984493](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39711984493), producer `39711112456` |
| Manual Reproducible Release with `publish=false` | **PASS**; both clean builds and original JAR equal canonical; exact native/full-stack evidence reproduced; both pack staging gates successful | [39712892387](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39712892387), job `119608145896`, `workflow_dispatch` / `master` / source `9075ea8` |
| Public 4.1.76 release | **HELD; not published** | Explicit maintainer approval of the verified concrete four-asset candidate is still required |

The 10 successful direct PR workflow runs are
[39710160519](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160519),
[39710160552](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160552),
[39710160557](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160557),
[39710160617](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160617),
[39710160597](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160597),
[39710160602](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160602),
[39710160605](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160605),
[39710160534](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160534),
[39710160537](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160537),
and [39710160510](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39710160510).
Their test checkout may use the PR merge source
`b0e4045ee9b561a0e87a6d265e0a061d6670ca81`; that is distinct from the reviewed
branch head and final normal merge. Only the fresh `9075ea8` artifacts below are
accepted final release inputs.

### Exact compiled and packaged identities

| Artifact | Bytes | SHA-256 | Producer or source |
| --- | ---: | --- | --- |
| `Slimefun-Legacy4.1.76.jar` (canonical bytes) | 8,684,431 | `be58eef8965eeb31fb930e6cfa204f74f221f95bf649976eb17802886c859916` | Canonical run `39711112456`, artifact `12397541205` |
| `SF_Addons_1.21.11-26.3.zip` / r145 | 28,195,295 | `a2c6f61dc3cc89a01e9f1606a0c6881a250c9066546de509bc3052c4e8bafd9d` | Canonical run `39711112456`, artifact `12397406749` |
| `SlimefunLegacyRP.zip` (official Java resource pack) | 9,143,959 | `1b856fff90fe78b7d5964a86a8ed281517d073a082db485d73f31cd07aa64a83` | Official `wickidcow/SFL_RP_Official` / `v4.0.1`, asset `619496149`; unchanged `compatibility/resource-pack-release.json` |
| `SFL_GEYSER_RP_experimental_v1.0.3_complete.zip` | 2,390,264 | `60fb9fcfe19e7e5644ff7202fd83bcd2b73b9f7685f3a57797d73877153c014c` | Committed `compatibility/bedrock/` archive at source `9075ea8` |

Both downloaded GitHub artifact containers match their API sizes and SHA-256
values before extraction. The final JAR passes the strict source/version/Java 21
bytecode verifier, including all seven required runtime classes. The addon ZIP
passes safe paths, outer and all 45 inner JAR CRCs, exact maintained-addon set,
all embedded versions and source pins, manifest/checksum agreement, and r145/core
source binding. Closing API snapshots preserve both original artifact identities
and their successful producing jobs. The final main build also passed its build,
invariant, release-evidence control and metadata gates.

The canonical receipt is `bedrock-complete-final-bundle-verification.json`,
SHA-256 **`49f6145de7cd3c4aebe20f7a597f7da460eb83aafde8d745e0f49433a6bd388a`**.
Its final metadata-close receipt is
`bedrock-complete-final-canonical-metadata-close.json`, SHA-256
`2a9ddbe3aaf6a3c259d5526881e8d4c186df4aad848bb73d8442674ee737517c`.
Local originals remain under
`/tmp/networks-completion-20261021/artifacts/bedrock-complete-final/canonical-core/`
and `canonical-bundle/`; the run/artifact IDs above identify the hosted originals.
The initial restricted-sandbox download could not open a socket; the authorized
read-only download succeeded with exact API identity and required no source change.

The important addon identities are unchanged:

| Addon | Bundled version | Exact source commit | JAR SHA-256 |
| --- | --- | --- | --- |
| Networks Expansion | 1.0.60 | `d41d362c8b71073dca41abc24f6ef6a5a8688fff` | `e355ce958bd1e3d3c8ddd65d7f56dbd2b8d4c605ca6b0f1025a34e65c6a808b2` |
| InfinityExpansion2 | 2.0.15 | `168815bb99e5701d3680095a9eb9170d83a19740` | `897bd4de70c9219217ecfb0f8cf68f0147b6c38758a239085db39718dd686eef` |
| GeneticChickEngineering | 1.0.4 | `a46359e675fe21b509642698fd77d75580436155` | `d3bea54d2d47a5d031ec7c504f772ac5151634aa7025b88b12ce9db36fd55162` |

### Final runtime and asset-preservation evidence

- Native run `39711192917` passed both original two-JVM paired storage lanes on
  Purpur 1.21.11 build 2568 and Purpur 26.3 build 2652, using the exact canonical
  core, Networks and IE2 bytes. Native entity-retirement probes passed 26
  assertions on Purpur 26.3 build 2646 and 27 on Folia 26.3 build 3, with normal
  shutdown. Strict acceptance is `PASS_EXACT_RELEASE_NATIVE_PAIR`, recorded in
  `bedrock-complete-final-native-verification.json`, SHA-256
  `9ef7764b0cd6ef8ce128de41abc4542d65e5b9adcabc949bb4c2b21a76351b37`.
  This covers the actual storage/lifecycle fixtures; it does not certify every
  client transaction, crash recovery case or cross-region addon interaction.
- Folia run `39711323021` reproduced the original 12-addon admission report,
  installed identities and runtime selection from the final canonical ZIP. Both
  Folia 26.3 build 5 ALPHA boots enabled GCE **1.0.4**, registered **64 chickens**,
  logged no ERROR/SEVERE messages and shut down normally. Receipt
  `bedrock-complete-final-folia-verification.json`, SHA-256
  `0691a103f9ac7aa370fac378f4d4221d77b049c5594eafc0987e6ab0df527359`, records
  `PASS_EXACT_SOURCE_FOLIA_DECLARED_ADDON_STARTUP`. Existing experimental-scheduler,
  offline-fixture, storage-pool and missing optional integration warnings remain
  visible. This establishes startup/restart acceptance for the admitted subset,
  not full chicken gameplay or full-stack/cross-region Folia compatibility.
  **Networks and IE2 remain excluded and unsupported on Folia runtime.**
- Automatic full-stack run `39711984493` completed all seven jobs. The strict
  verifier binds its original core/bundle and four runtime artifacts to canonical
  run `39711112456`, source `9075ea8` and the exact accepted hashes. All six
  downloaded containers passed API size/hash, safe-path and CRC checks; closing
  run/attempt/job/artifact metadata remained stable. Paper 1.21.11 build 132,
  Paper 26.2 build 134, Paper 26.3 build 211 and Purpur 26.3 build 2646 each passed
  both stack boots with all 45 addons enabled, normal shutdown and no ERROR/SEVERE
  messages. All 16 Black Market seed/verify/missing/restored phase boots passed.
  The Paper 26.3 Networks/Fluffy native fixture also passed its rich-PDC and item
  count conservation check. Receipt `bedrock-complete-final-fullstack-verification.json`,
  SHA-256 `11311c824cf1f5737321511eb649fa7e173f209924c62152326eae0fff8bae09`,
  records these exact-input startup/restart and bounded fixture results. Existing
  warnings remain in the original logs; this does not establish universal
  gameplay, client-click, arbitrary crash or full-stack Folia certification.
- Hosted cleanup run `39711112172` passed the strict preservation verifier.
  `delete-ids.txt` is empty; before and after release metadata are byte-identical.
  All four v4.1.75 IDs, sizes and digests remain unchanged: core `650941345`, addon
  ZIP `650941344`, official Java pack `650941348`, and current Bedrock overlay
  `664360404`. The overlay remains 1,265,679 bytes with SHA-256
  `90d78fcf8382bdee1bce3a364515769cb8325c174b58c34b512039502cc50e51`.
  Receipt `bedrock-complete-final-cleanup-verification.json`, SHA-256
  `af2bb72218626cb9cb83bc13068f070a0a30e19603343615fb6e73fd461a0ff0`,
  records **`PASS_ZERO_DELETIONS`**. No public asset was changed by this workstream.

### Final validation-only release acceptance

Manual [Reproducible Release 39712892387](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39712892387)
completed successfully with **`publish=false`**, event `workflow_dispatch`,
branch `master`, exact source `9075ea8`, attempt 1 and job `119608145896`.
Both actual clean-build log hashes and the independently downloaded raw JAR
(artifact `12397143444`) equal canonical SHA-256
`be58eef8965eeb31fb930e6cfa204f74f221f95bf649976eb17802886c859916`.
The unchanged release-artifact verifier accepts its source, version, Java 21
bytecode and all seven critical runtime classes.

The original `release-runtime-evidence` artifact `12397178230` is 105,667,415 bytes
and passes API digest/length, extraction/path and CRC checks. The unchanged
native and full-stack verifiers reproduce the original PASS results against
canonical run `39711112456`, native run `39711192917` and full-stack run
`39711984493`, with the exact core/bundle bytes in the table above. The separate
Folia receipt remains the accepted evidence for its 12-addon startup subset.

Both resource-pack staging gates passed their original metadata/archive and
unchanged-copy checks. The official Java pack retains its unchanged pin; the
complete optional Bedrock pack comes from the accepted repository archive with
no dependency on removed public source assets. The staged packs were not
separately uploaded as validation artifacts; their acceptance is supported by
the immutable pins and actual successful hosted verification/copy gates.
Candidate completion succeeded. **Publishing and release-asset normalization
were skipped.** Closing run/attempt/job/step/artifact metadata remains stable.

Receipt `bedrock-complete-final-release-validation.json`, SHA-256
**`b38a6b4f3c1204c94af54f6ebd505e2d8a8232b50e3ac8fa03e92f4d1f9857dd`**,
records **`PASS_MANUAL_PUBLISH_FALSE_RELEASE_VALIDATION`**. This is successful
release validation; it does not grant publication approval or extend the bounded
runtime/Bedrock-client claims above.

### Closing public state

The closing API snapshot at **2026-10-22 02:45:57 UTC** records all **14** listed
exact-source `9075ea8` workflow executions successful, including manual
Reproducible Release `39712892387`. Its original artifacts were then accepted
independently as recorded above. `master` still points to
`9075ea852095b28543aaa1456bc2576778cb4c4d`; no `v4.1.76` tag exists, and no
`v4.1.76` release appears in the latest 15 releases. All four current v4.1.75
asset identities match the preservation evidence above. Snapshot:
`bedrock-complete-final-public-state.json`, SHA-256
`e99ce52c21cf8698e2a24855f9e22e77dbecaa70272fbf0e57352a0edef2ad4b`.
No publication was authorized or performed by this workstream.

### Files changed, publication boundary and exact next action

PR #417 contains the schema 2 Bedrock pin, complete ZIP and component provenance;
archive verifier/tests; preservation policy/tests; reproducible release workflow
and its real-shell tests; README, Bedrock installation guide, 4.1.76 notes and the
preceding checkpoint. This new evidence snapshot changes only the permanent
checkpoint and its acceptance receipt; it does not change production code, the
version, dependency pins, release inputs or accepted compiled source.

**Required technical gates are complete for this reviewed candidate.** The final
canonical build, native paired storage, full-stack runtime, declared-Folia startup,
asset preservation and manual `publish=false` release validation have all passed
with exact-source evidence. The documented scope limits and 107 legacy Geyser
warnings remain. Core 4.1.76 is still **unreleased and held for explicit maintainer
publication approval**; no further version bump is needed.

**Exact next action:** present the concrete four-asset `v4.1.76` publication from
source `9075ea852095b28543aaa1456bc2576778cb4c4d` for explicit maintainer approval,
with this checkpoint, its acceptance receipt and tracker
[#378](https://github.com/wickidcow/Slimefun-Legacy/issues/378) preserving the final
results. After approval, run the protected publisher with the accepted source
and evidence, then verify the actual public tag, release and all four uploaded
asset names, sizes and hashes against the table above. Until that approval, keep
publication held. Do not publish unrelated Slimefun changes, advance the accepted
release source merely to record evidence, or restart the accepted GCE, Networks
and IE2 repairs.

## Historical intermediate handoff — replacement Bedrock pack 0.0.2

PR [#416](https://github.com/wickidcow/Slimefun-Legacy/pull/416) is merged at
`4c2bdf4edc685afbfaa81cde168252b19094e428`. Its requested optional Bedrock
carryover and Geyser installation documentation are implemented. All 12 PR
workflows passed before the normal merge. The following exact-merge checks passed:

- Canonical [39703387481](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39703387481):
  48/48 jobs, all 45 addon JARs verified. Core SHA-256
  `ad7226076b5ecafc617ff62cd05c2250a6cca22e893fe753143f5a0493e452b3`;
  r145 ZIP SHA-256 `3553748164cdc4022b9e0b4d7f952d17d9dceb38bba4236b47e02eb38d9de192`.
- Native [39703768197](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39703768197):
  six jobs passed, strict exact-release paired storage/retirement verification passed.
- Automatic full-stack [39704405884](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39704405884):
  seven jobs and all four runtime lanes passed. Original artifacts passed the strict
  producer/source/input verifier against canonical run 39703387481.
- Folia admission/runtime [39703994390](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39703994390):
  both jobs passed. Both Folia 26.3 build 5 ALPHA boots enabled GCE 1.0.4,
  registered 64 chickens and shut down normally. Installed core and all 12 admitted
  addon identities reproduce exactly from the canonical artifacts. This establishes
  startup acceptance; it does not establish full chicken/cross-region gameplay.
  Networks and IE2 remain excluded and unsupported on Folia runtime.

### New source-asset change and concrete repair

During validation, the public v4.1.75 release replaced the selected
`GEYSER_SFL_RP_Experimental_v0.0.1.zip` (asset 664136278) with
`GEYSER_SFL_RP_v0.0.2.zip` (asset **664289959**), uploaded on
2026-10-22 at 01:13 UTC. No release assets were changed by this workstream.
The original 0.0.1 bytes were retained locally before the replacement.

The earlier direct cleanup [39703387561](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39703387561)
passed with zero deletions before the external change. Afterward, reproducible
run [39703387579](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39703387579)
failed at the Bedrock source size check; both clean core builds had already passed
byte equality. Cleanup follower [39704405847](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39704405847)
refused the unreviewed 0.0.2 filename before deletion. These are actual failed
release checks, not failed plugin compilation or runtime tests.

Branch **`release/4.1.76-bedrock-pack-v002`**, based on `4c2bdf4e`, prepares the
currently published replacement as a reviewable, held candidate. The version
change and additional content were stated explicitly; no affirmative maintainer
answer choosing 0.0.2 or authorizing publication has been received. Core remains
4.1.76/r145, with all 45 addon pins unchanged. This scoped development does not
publish, restore, delete or replace any public asset.

- Current archive: **1,329,705 bytes**, SHA-256
  `b27941425a646ba97c4789ecf2841e20f08663e79b3d538b552516d40cc67ee1`.
- Contents: the unchanged Slimefun `.mcpack`, 20 legacy Slimefun mapping JSONs,
  two additional Albion ValhallaMMO packs, one format-v2 Valhalla mapping JSON
  (507 item definitions), and one custom-skull mapping JSON (1,453 skin hashes).
  Three Slimefun mapping files remove duplicates/an invalid item key and separate
  the sugar-based zinc-dust name. This is a substantive archive replacement.
- Read-only inspection passed outer/three inner CRCs, safe unique paths and all
  1,175 strict JSON parses. No Geyser JAR, extension JAR or server configuration is
  included. Archive inspection does not establish Bedrock client rendering.
- Changes in this branch: the exact replacement pin, scoped archive validators
  for its three pack/mapping schemas, exact preservation policy and rejection
  tests, release-workflow filename and integration fixtures, README/release/install
  documentation and this checkpoint. Future/unknown assets still fail closed.
- Focused follow-up verification: **47 preservation**, **36 archive-verifier**,
  and **7 actual release-workflow shell tests** pass normally and under optimized
  Python; the shell suites propagate optimization into their helper subprocesses.
  All **26 release dispatch/evidence controls**, the complete invariant suite, YAML
  parsing and 14 embedded Bash syntax checks pass. Independent bounded reviews of
  the verifier and preservation/workflow/docs changes are clear.
- Actual isolated Geyser **2.12.0 build 1268** / Java 25.0.4.1 loader check passes:
  all three supplied packs loaded, all **1,453 skulls** registered, zero client
  connections and normal shutdown. Every supplied file remained byte-identical.
  The **107 texture-size deprecation warnings** remain documented; Bedrock rendering,
  item interactions, embedded Spigot behavior and production connectivity were not
  tested. Initial direct-DNS failure and one cold-cache Mojang texture timeout are
  retained; the final warm-cache run fetched the missing texture and passed.
- Initial shell fixture incorrectly used a non-Albion icon prefix; the real helper
  rejected it. The fixture was corrected and both full shell-suite modes passed.
  Initial local build setup lacked Git metadata, and an overlapping retry interfered
  with generated test files. Both clients were stopped and diagnostics retained;
  one clean isolated build then passed **941 tests / 162 suites, zero failures or
  errors and one existing external-database skip**, plus Spotless and the Java
  deprecation/removal gate. No production
  code or test gate was changed to accommodate these environment failures.
- The successful plugin and runtime receipts above belong to `4c2bdf4e`; do not
  relabel them as final-source acceptance for this later commit.

### Additional external replacement before commit

The final source read found that public v4.1.75 had replaced 0.0.2 again with
`SFL_GEYSER_RP_experimental_v1.0.3.zip`, asset **664360404**, 1,265,679 bytes,
SHA-256 `90d78fcf8382bdee1bce3a364515769cb8325c174b58c34b512039502cc50e51`.
The completed 0.0.2 implementation and tests are preserved in this branch, but
its old origin is no longer available. Do not merge this 0.0.2 snapshot as an
accepted release candidate. Compare the new archive against the preserved bytes,
then update only the affected pin/layout/docs and relevant tests. Production
Java, addon source pins and the completed repair findings remain unchanged.

### Exact next action

Finish the bounded 1.0.3 archive comparison and update this held candidate to the
stable current source. Reuse the completed plugin findings; run affected asset
checks and then the required hosted checks on the final source. Require current
source metadata, exact ZIP identity and all runtime/equality gates before the
final manual `publish=false` validation. Keep tracker
[#378](https://github.com/wickidcow/Slimefun-Legacy/issues/378) current with actual
commit/run/artifact evidence. Publication remains held until explicit maintainer
approval of the concrete verified four-asset release candidate.

## Historical PR #416 handoff — original Bedrock pack carryover

The maintainer explicitly requested carrying `GEYSER_SFL_RP_Experimental_v0.0.1.zip`
into the next release, describing it as optional for Bedrock players and stating
that Geyser and the supplied drop-in files are required. This authorizes the
specific asset inclusion and preservation policy; core/addon publication remains
held. Core stays at **4.1.76**, bundle revision **145**, and all 45 addon source pins
remain unchanged.

- Starting master: `f472c473b6a2013be29403061785e90d32d1c868`, accepted r145 predecessor.
  Branch: `release/4.1.76-optional-bedrock-pack`.
- Approved source: v4.1.75 release `415923695`, asset `664136278`, 226,576 bytes,
  SHA-256 `ba4fa277fb71a33ca557e0206ea51c40680593952a5d47fbd849b335c9fe09bf`.
  The unchanged ZIP contains `Geyser-Spigot/packs/SlimefunBedrockRP.mcpack` and
  20 custom-mapping JSON files. Both outer and inner ZIP CRCs and all mapping JSON
  parses pass. This verifies archive identity/structure, not every Bedrock texture
  or client interaction.
- Release changes: a separate checksum/source pin, read-only archive and metadata
  verifier, four-asset staging/publishing/normalization, and an exact preservation
  exception for this ZIP on its origin v4.1.75 and approved successor v4.1.76.
  Unknown assets, changed bytes and unapproved tags still fail; the older Geyser
  alpha ZIP is not approved by this request. The existing Java pack pin remains
  unchanged. No repacking, plugin Java change, live-server edit or public-asset
  replacement is part of this change.
- Documentation: README, release notes and
  [Bedrock installation instructions](docs/bedrock-resource-pack.md) explicitly
  require a configured Geyser installation plus both `packs/` and
  `custom_mappings/` contents. The optional download is a fourth separate asset,
  outside the addon JAR ZIP.
- Focused tests: **45 preservation tests**, **23 Bedrock asset-verifier tests**,
  and **7 tests executing the actual workflow shell blocks with local GitHub
  stubs** pass normally and under optimized Python. The 26 existing release
  dispatch/evidence controls also pass with the Bedrock acquisition gate required.
  The complete invariant suite also passes with the new shell suite wired into
  its normal repository-root entry point. The isolated CI-sequence Java build
  passes **941 tests / 162 suites, zero failures/errors and one existing
  real-database skip**; those local JARs are not release artifacts.
  The actual current v4.1.75 snapshot now preflights with four retained assets and
  zero deletion candidates. The original failed alpha snapshot remains rejected.
- Initial validation failures are retained: Gradle/local HTTP fixtures cannot open
  their sockets in the restricted sandbox; normal execution outside that sandbox
  runs the checks. An unformatted local Gradle build reaches the pre-existing
  Spotless violations in the untouched base. Verification uses the repository's
  existing CI formatter-before-build sequence in a disposable copy, without
  introducing unrelated formatting changes into this branch. A first cleanup
  test run preceded creation of the shared pin and failed on that missing file;
  the completed normal/optimized runs pass after the pin exists.
  Review also caught the new shell suite treating the invariant runner's root
  argument as a test name; that invocation was reproduced, corrected, and
  verified through the complete invariant run plus the optimized root invocation.

### Accepted predecessor and resolved follow-ups

The three-asset f472c473/r145 candidate passed canonical bundle
[39666239520](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39666239520),
native storage/retirement
[39666239574](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39666239574),
automatic full-stack
[39668045172](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39668045172),
and final `publish=false` reproducible validation
[39669276799](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39669276799).
Those exact-source receipts belong to f472c473; the new release workflow requires
acceptance on its own final merge source before publication.

GCE PR #4 is merged at `a46359e675fe21b509642698fd77d75580436155` and selected as
1.0.4 in r145. Its actual JAR matches both original installed receipts from
[Folia run 39666239448](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39666239448).
Both boots enabled GCE, registered 64 chickens and shut down normally. The known
startup scheduler defect is resolved; full chicken/cross-region gameplay is not
certified. Networks and IE2 remain excluded from this Folia subset.

The newer IE2 test-fixture compiler failure was repaired by
[PR #36](https://github.com/wickidcow/SF_InfinityExpansion2/pull/36), merged at
`b1fd91db9e85189fd108b45e343e32cead9c2dde`. The actual targeted retry
[119544575926](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39666239493/job/119544575926)
passes; the overall run is successful on attempt 2. Separate full-build evidence
records 183 tests, zero failures/errors/skips. This test-only repair leaves the
published IE2 2.0.15 pin and r145 plugin bytes unchanged.

### Historical next action before PR #416 merge

Complete review and normal hosted checks for this scoped carryover change, merge
it, then accept the final merge source through the existing exact-source bundle,
native and full-stack gates and `publish=false` release validation. Keep tracker
[#378](https://github.com/wickidcow/Slimefun-Legacy/issues/378) current with actual
PR/merge/run results. Publish only after explicit maintainer authorization, with
all four assets checked against their accepted bytes. Do not restart the accepted
Networks/IE2 repairs or substitute predecessor artifact hashes for a new source.

## Historical r145 integration handoff before f472c473 acceptance

- PR [#414](https://github.com/wickidcow/Slimefun-Legacy/pull/414) merged as `e7ba40469eae1aa54b4347af19e58341f492edcb`, integrating the published Networks 1.0.60 / InfinityExpansion2 2.0.15 pair into held r143.
- PR [#415](https://github.com/wickidcow/Slimefun-Legacy/pull/415) merged as `513d316f65f7701a75f4289aa92e886eae363a06`, advancing only CrystamaeHistoria to 1.0.2 and MobCapturer to 1.0.7 in r144. All 43 other source selections retained r143.
- The r144 [canonical bundle](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39634483945) and [full-stack acceptance](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39634484086) passed on PR head `3ad4b207b7173978a794e0a9c361f2d2c2023235`. These results belong to that tested source; they do not establish final r145 acceptance.
- PR [#413](https://github.com/wickidcow/Slimefun-Legacy/pull/413) is resumed against the merged core work. Its declared-addon Folia startup lane exposed GeneticChickenEngineering 1.0.3's inherited startup tick counter calling the Bukkit scheduler before enable completes. The r145 candidate advances only GeneticChickenEngineering to 1.0.4 for native Folia startup scheduling; all 44 other r144 addon entries remain unchanged. Relative to published r141, seven addon source selections advance and 38 remain unchanged.
- This work covers startup and load evidence for the audited declared-addon subset. It does not add Folia declarations, establish chicken gameplay or cross-region safety, or certify the complete 45-addon bundle. Direct Networks and InfinityExpansion2 changes remain with their separate repair workstream.
- GeneticChickenEngineering [PR #4](https://github.com/wickidcow/SF_GeneticChickEngineering/pull/4) merged as `a46359e675fe21b509642698fd77d75580436155`, now selected by r145. Its [hosted compatibility run](https://github.com/wickidcow/SF_GeneticChickEngineering/actions/runs/39661722799) passed all three API lanes and packaged ABI/ownership checks; publication was skipped. The r145 native and full-stack acceptance and final reproducible release validation remain **pending**. Core stays at **4.1.76**; addon and core publication remain held. No new release, tag or public asset replacement is authorized by these changes.

### Historical next actions before f472c473 acceptance

1. The bounded GeneticChickenEngineering startup repair is accepted and pinned. Preserve its exact source, all 44 other complete addon entries and the publication hold during integration.
2. Complete PR #413's exact-source declared-addon startup and receipt checks. Record actual results and retained limitations; compile or descriptor admission alone is insufficient.
3. On the final accepted core source, require the canonical 45-addon bundle, native gates and automatic full-stack follower to pass. Earlier r143/r144 evidence cannot replace these results.
4. Run Reproducible Release with **publish=false** on that exact source. Preserve all source, JAR, ZIP and resource-pack equality checks, then append concrete run and artifact evidence here before requesting publication approval.

The r143 chronology below retains its original sources, failures, test results and instructions as historical evidence. Its then-pending actions and PR status do not supersede this current handoff.

## Historical r143 starting points

- Core master: `1cb32d6e95b305998065b8ef6b936a56f679187d`; project version already **4.1.76**. Preserve merged backpack ownership, pending-removal ordering and scheduler cleanup fixes from PRs #408–412.
- Published core baseline: [v4.1.75](https://github.com/wickidcow/Slimefun-Legacy/releases/tag/v4.1.75), source `7f702e3565a381aeeefd99555f2c8fe818858e9c`, canonical bundle **r141**. Its ZIP SHA-256 is `322c7b4b7dd06a46f15f35235c8b5cfaf6092f0381300aeff02ce6be375b5813`.
- Held canonical selection: **r142**, 45 addons. JEG 2.1.73 and SlimeHUD 2.0.5 already selected; MagicExpansion 1.1.16 and FinalTECH 3.0.16 retained.
- Released [Networks 1.0.60](https://github.com/wickidcow/SF_NetworksExp/releases/tag/v1.0.60): source `d41d362c8b71073dca41abc24f6ef6a5a8688fff`, `SF_Networks1.0.60.jar`, 1,681,029 bytes, SHA-256 `e355ce958bd1e3d3c8ddd65d7f56dbd2b8d4c605ca6b0f1025a34e65c6a808b2`. Production PR #104 and publication run [39537659539](https://github.com/wickidcow/SF_NetworksExp/actions/runs/39537659539) completed.
- Released [InfinityExpansion2 2.0.15](https://github.com/wickidcow/SF_InfinityExpansion2/releases/tag/v2.0.15): source `168815bb99e5701d3680095a9eb9170d83a19740`, `SF_InfinityExpansion2.0.15.jar`, 1,707,539 bytes, SHA-256 `897bd4de70c9219217ecfb0f8cf68f0147b6c38758a239085db39718dd686eef`. Production PR #32, publisher repair #34 and publication run [39539123498](https://github.com/wickidcow/SF_InfinityExpansion2/actions/runs/39539123498) completed.

The previous separately assembled **r140** repair ZIP used an outdated r139 baseline. It must not replace the current canonical bundle: that would regress newer MagicExpansion and FinalTECH selections. Build r143 from the complete r142 matrix, then supersede the old handoff artifact.

## Historical r143 implementation

- Advance canonical bundle **r142 → r143** with only the two released addon source pins changed. Preserve all 43 other complete addon entries and existing compatibility/naming metadata; 41 source pins remain unchanged relative to published r141.
- Align the paired fixture sources/versions and r135 native probe's r143 acceptance with the released pair. Admit r143 in the Black Market probe with the unchanged MagicExpansion source. Retain older accepted revision cases and changed-source rejection controls.
- Stage the same hash-pinned published universal JARs in the canonical bundle and native storage runtime. Preserve separate newer-API compilation, source rebuilds/tests and exact candidate-core compile/test classpath receipts. Do not distribute the 26.3 probe outputs for this pair.
- Preserve complete JAR and ZIP equality, quantity conservation, two independent JVMs, read-only post-exit database snapshots and normal shutdown requirements. Runtime support for Networks/IE2 on Folia remains unsupported.
- Add validation-only release dispatch with explicit publishing gates. Keep both independent core builds, exact canonical bundle/native/full-stack collection and pinned resource-pack checks required.
- Update README, candidate notes and bundle metadata while keeping core version **4.1.76**.

## Historical r143 verification and failures

- Independently compared r143 to committed r142: exactly 45 addons, only Networks and IE2 source pins changed, all other 43 complete entries identical.
- Downloaded the published r141 ZIP: archive CRC, all 45 inner JAR hashes, source matrix and overall SHA-256 verified.
- Downloaded both final public addon JARs: complete bytes, sizes, versions and CRC verified against the pins above.
- Published-pair staging/API-floor tests: **18 passed**, including rejection of wrong source, same-version different bytes, newer API/bytecode and unsupported Folia declaration.
- Release dispatch/evidence contract suite: **26 passed**, including red-before/green-after proof that omitted or false publishing must not mutate releases.
- Full Python discovery: **548/548 passed normally and 548/548 passed with `python3 -O`**, no failures/errors/skips, including localhost download fixtures. New rejection cases demonstrated RED before the additional publication/compiled-input checks and GREEN afterward.
- Complete `scripts/verify_legacy.py .` invariant suite: **PASS** after recognizing the explicitly requested active completion checkpoint in the root-document allowlist. All historical documentation guards remain active.
- All three changed workflows: YAML and embedded Bash syntax **PASS**; independent bounded reviews **CLEAR**.
- Full local Java build: **PASS** in an isolated `/tmp` snapshot: 162 JUnit XMLs, **941 reported / 940 passed / zero failures or errors / one existing external-database assumption skip** (`DatabasePatchV3RealDatabaseTest.setUp:33`). `spotlessApply`, `clean`, full `build`, Spotless and deprecation/removal gate all passed; zero deprecation warnings. The 286 temporary formatting changes stayed outside the repository. This is working-snapshot validation, not final release artifact identity. Initial environment failures were missing JDK tools, blocked localhost sockets and the downloaded JDK not using the system CA trust store. A shared-checkout formatting failure and concurrent invariant read were retained as failed diagnostics; isolated formatting and Spotless now pass. No gate was disabled and no production Java edits are included.
- Final merged-master native, canonical-bundle, exact full-stack and reproducible release gates: **pending**. Earlier r142 runs and addon release tests do not substitute for the exact new candidate.

### Historical PR #414 hosted acceptance and blocker

Evidence below belongs to PR head `f84ca26a9495241816e79955df5fcee2caa0d5ee`, tested merge source `5cd321ad94c89f837f0703908d68e790592da58a`; it is not final merged-master release evidence.

- [Core build 39612997736](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39612997736): **PASS**, full build/invariants and release evidence controls; zero deprecation warnings.
- [Public API 39612997962](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39612997962): **PASS**, all 1,564 baseline signatures unchanged.
- [Native storage 39612997745](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39612997745): **PASS**, all six jobs. Paired storage passed on Purpur 1.21.11/2568 and 26.3/2652: 24 roundtrips, 192 tagged items conserved, exact 192-item withdrawal after independent JVM restart, normal shutdown and original read-only post-exit database checks. Both input/result archives were downloaded, hash-checked and passed the unchanged receipt validators.
- [Native contract tests 39612997742](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39612997742): **PASS**, 34/34. Required addon runtime, compatibility comparisons, migration, maintained compile, Paper preflight and platform smoke workflows also passed.
- Canonical/native PR core JARs are byte-identical: 8,684,448 bytes, SHA-256 `768c2fccb71a6468a7bd970c35cd606804c956cf28c0694d2155e8f1aad9579e`. Runtime Networks/IE2 JARs match the published hashes above. The separately formatted main-build JAR is not a substitute for this runtime identity.
- Pinned official resource pack [v4.0.1](https://github.com/wickidcow/SFL_RP_Official/releases/tag/v4.0.1): **PASS** through the existing release verifier and full ZIP CRC. Actual public asset `619496149` is 9,143,959 bytes, SHA-256 `1b856fff90fe78b7d5964a86a8ed281517d073a082db485d73f31cd07aa64a83`; source tag `22452a85ba96170e9fac4ef0a7d4743d1034a775`, 10,892 ZIP entries. The pin remains unchanged.
- [Canonical bundle 39612997890](https://github.com/wickidcow/Slimefun-Legacy/actions/runs/39612997890): Networks and IE2 jobs **PASS**, but RykenSlimeCustomizer job `119268200306` failed resolving `me.clip:placeholderapi:2.11.6` and `de.tr7zw:item-nbt-api-plugin:2.15.1`. The earlier Minebench mirror returned `Network is unreachable`; follow-up requests returned HTTP 503 while the existing official repositories returned HTTP 200 XML. Source compilation did not begin. Full-stack and Folia admission consumers cannot accept this failed bundle.
- The initial two-module routing prototype passed its first fixture but **FAILED** the real pinned RSC compile at inherited `de.tr7zw:item-nbt-parent:2.15.1`, still queried at Minebench. It was not committed as accepted. The official child POM confirmed this exact parent; the parent has no further parent or imported BOM, and its listed dependencies are provided. The corrected fixture demonstrated **RED** against that incomplete filter by parsing the child and inherited parent POMs through real Gradle.
- Final repair: a 12-line ephemeral compile-probe filter excludes exactly `me.clip:placeholderapi`, `de.tr7zw:item-nbt-api-plugin` and `de.tr7zw:item-nbt-parent` at the exact parsed `repo.minebench.de` host. All source pins, dependency versions, unrelated modules, other hosts, repository order and release evidence gates remain unchanged. Normal and optimized Python/real-Gradle regression runs both **PASS**, no skips, with seven exact JAR coordinates retained and parent POMs requested from the declared provider. Independent review is **CLEAR**. The repository invariant suite also passed with JDK 25 during this repair.
- Actual pinned RSC source `e62b10423a64d1940ee4bc87947e2ff42b0ee3df`: **PASS**, Gradle 9.6.1 `clean assemble --no-daemon --no-build-cache` against Paper `26.3.build.211-stable` and the exact PR core hash above; exit zero, build successful in 23 seconds. No addon source/build/dependency content changed. The first local attempt stopped during core installation because Maven lacked task-local proxy settings; that failed diagnostic and the later parent-POM failure are retained separately. No merge or release has occurred; the next gate is hosted CI on this repaired PR head.

## Historical r143 changed files and branch

Working branch: `release/4.1.76-network-pair-r143`, based on `1cb32d6e95b305998065b8ef6b936a56f679187d`. Implementation commit: `660e0aa53a676b507095a24883d12f327ffa824a`. Integration PR: [#414](https://github.com/wickidcow/Slimefun-Legacy/pull/414), open and ready for review; final GitHub gates are pending. Local verification and bounded independent reviews passed.

Files: canonical matrix, `gradle.properties`, README, `docs/releases/4.1.76.md`, this checkpoint; canonical bundle/native/reproducible workflows; published-pair staging helper and rejection tests; paired fixture lock/runner and contract tests; r135 and Black Market fixtures and native contract tests; release evidence synthetic fixtures and dispatch controls; root documentation allowlist for the required checkpoint; `scripts/compile_addon_paper_26_3.py` and its real Gradle routing regression. Production Java remains unchanged.

## Historical r143 next actions

1. **Local verification complete:** full build, invariants and 548 normal/optimized Python controls passed; production Java is unchanged.
2. The narrow RykenSlimeCustomizer dependency-routing repair and actual pinned compile are verified. Follow PR #414 CI on its latest head, including the repair and this checkpoint. Require successful relevant CI, including canonical bundle and native pair, before merging to master. Do not merge unrelated failing draft PR #413.
3. On the exact merged master, require Native Entity Retirement and canonical 45-addon bundle success, then the automatic full-stack follower triggered by that exact bundle run. Manual full-stack dispatch currently selects the published release bundle and is unsuitable here.
4. Run Reproducible Release with **publish=false** on that exact master. Preserve every full-source/full-JAR/full-ZIP evidence comparison. Verify all three proposed assets and save the canonical r143 bundle, superseding the outdated r140 handoff.
5. Update release tracker [#378](https://github.com/wickidcow/Slimefun-Legacy/issues/378) and the Networks completion handoff with concrete commit/run/artifact evidence. Request core publication approval only when the verified release is ready.
