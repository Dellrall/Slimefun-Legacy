# Networks Expansion — core release integration checkpoint

Updated: 2026-10-21. This file tracks the coordinated **Slimefun Legacy 4.1.76 / r143** integration. The completed addon development remains recorded in [Networks' permanent checkpoint](https://github.com/wickidcow/SF_NetworksExp/blob/master/NETWORKS_EXPANSION_COMPLETION.md). Consult this file and current Git state before resuming; do not repeat accepted production repairs.

## Publication boundary

Core **4.1.76 remains unreleased and held for explicit maintainer approval** after the concrete candidate is verified. Continue integration, testing, review and merge without restarting the addon repairs. Do not publish a core tag/release or replace existing v4.1.75 assets during validation. `reproducible-release.yml` now defaults manual dispatch to `publish=false` and requires explicit `publish=true` plus successful runtime evidence for either publishing or normalizing assets.

## Accepted starting points

- Core master: `1cb32d6e95b305998065b8ef6b936a56f679187d`; project version already **4.1.76**. Preserve merged backpack ownership, pending-removal ordering and scheduler cleanup fixes from PRs #408–412.
- Published core baseline: [v4.1.75](https://github.com/wickidcow/Slimefun-Legacy/releases/tag/v4.1.75), source `7f702e3565a381aeeefd99555f2c8fe818858e9c`, canonical bundle **r141**. Its ZIP SHA-256 is `322c7b4b7dd06a46f15f35235c8b5cfaf6092f0381300aeff02ce6be375b5813`.
- Held canonical selection: **r142**, 45 addons. JEG 2.1.73 and SlimeHUD 2.0.5 already selected; MagicExpansion 1.1.16 and FinalTECH 3.0.16 retained.
- Released [Networks 1.0.60](https://github.com/wickidcow/SF_NetworksExp/releases/tag/v1.0.60): source `d41d362c8b71073dca41abc24f6ef6a5a8688fff`, `SF_Networks1.0.60.jar`, 1,681,029 bytes, SHA-256 `e355ce958bd1e3d3c8ddd65d7f56dbd2b8d4c605ca6b0f1025a34e65c6a808b2`. Production PR #104 and publication run [39537659539](https://github.com/wickidcow/SF_NetworksExp/actions/runs/39537659539) completed.
- Released [InfinityExpansion2 2.0.15](https://github.com/wickidcow/SF_InfinityExpansion2/releases/tag/v2.0.15): source `168815bb99e5701d3680095a9eb9170d83a19740`, `SF_InfinityExpansion2.0.15.jar`, 1,707,539 bytes, SHA-256 `897bd4de70c9219217ecfb0f8cf68f0147b6c38758a239085db39718dd686eef`. Production PR #32, publisher repair #34 and publication run [39539123498](https://github.com/wickidcow/SF_InfinityExpansion2/actions/runs/39539123498) completed.

The previous separately assembled **r140** repair ZIP used an outdated r139 baseline. It must not replace the current canonical bundle: that would regress newer MagicExpansion and FinalTECH selections. Build r143 from the complete r142 matrix, then supersede the old handoff artifact.

## Implemented in this integration

- Advance canonical bundle **r142 → r143** with only the two released addon source pins changed. Preserve all 43 other complete addon entries and existing compatibility/naming metadata; 41 source pins remain unchanged relative to published r141.
- Align the paired fixture sources/versions and r135 native probe's r143 acceptance with the released pair. Admit r143 in the Black Market probe with the unchanged MagicExpansion source. Retain older accepted revision cases and changed-source rejection controls.
- Stage the same hash-pinned published universal JARs in the canonical bundle and native storage runtime. Preserve separate newer-API compilation, source rebuilds/tests and exact candidate-core compile/test classpath receipts. Do not distribute the 26.3 probe outputs for this pair.
- Preserve complete JAR and ZIP equality, quantity conservation, two independent JVMs, read-only post-exit database snapshots and normal shutdown requirements. Runtime support for Networks/IE2 on Folia remains unsupported.
- Add validation-only release dispatch with explicit publishing gates. Keep both independent core builds, exact canonical bundle/native/full-stack collection and pinned resource-pack checks required.
- Update README, candidate notes and bundle metadata while keeping core version **4.1.76**.

## Verification and failures

- Independently compared r143 to committed r142: exactly 45 addons, only Networks and IE2 source pins changed, all other 43 complete entries identical.
- Downloaded the published r141 ZIP: archive CRC, all 45 inner JAR hashes, source matrix and overall SHA-256 verified.
- Downloaded both final public addon JARs: complete bytes, sizes, versions and CRC verified against the pins above.
- Published-pair staging/API-floor tests: **18 passed**, including rejection of wrong source, same-version different bytes, newer API/bytecode and unsupported Folia declaration.
- Release dispatch/evidence contract suite: **26 passed**, including red-before/green-after proof that omitted or false publishing must not mutate releases.
- Full Python discovery: **548/548 passed normally and 548/548 passed with `python3 -O`**, no failures/errors/skips, including localhost download fixtures. New rejection cases demonstrated RED before the additional publication/compiled-input checks and GREEN afterward.
- Complete `scripts/verify_legacy.py .` invariant suite: **PASS** after recognizing the explicitly requested active completion checkpoint in the root-document allowlist. All historical documentation guards remain active.
- All three changed workflows: YAML and embedded Bash syntax **PASS**; independent bounded reviews **CLEAR**.
- Full local Java build: **PASS** in an isolated `/tmp` snapshot: 162 JUnit XMLs, **941 reported / 940 passed / zero failures or errors / one existing external-database assumption skip** (`DatabasePatchV3RealDatabaseTest.setUp:33`). `spotlessApply`, `clean`, full `build`, Spotless and deprecation/removal gate all passed; zero deprecation warnings. The 286 temporary formatting changes stayed outside the repository. This is working-snapshot validation, not final release artifact identity. Initial environment failures were missing JDK tools, blocked localhost sockets and the downloaded JDK not using the system CA trust store. A shared-checkout formatting failure and concurrent invariant read were retained as failed diagnostics; isolated formatting and Spotless now pass. No gate was disabled and no production Java edits are included.
- Final integration native, canonical-bundle, exact full-stack and reproducible release gates: **pending**. Earlier r142 runs and addon release tests do not substitute for the exact new candidate.

## Changed files and branch

Working branch: `release/4.1.76-network-pair-r143`, based on `1cb32d6e95b305998065b8ef6b936a56f679187d`. Local verification and bounded independent reviews passed. Integration commit and PR creation are next; record their identifiers at the next checkpoint.

Files: canonical matrix, `gradle.properties`, README, `docs/releases/4.1.76.md`, this checkpoint; canonical bundle/native/reproducible workflows; published-pair staging helper and rejection tests; paired fixture lock/runner and contract tests; r135 and Black Market fixtures and native contract tests; release evidence synthetic fixtures and dispatch controls; root documentation allowlist for the required checkpoint. Production Java remains unchanged.

## Exact next actions

1. **Local verification complete:** full build, invariants and 548 normal/optimized Python controls passed; production Java is unchanged.
2. Commit the independently reviewed integration diff and open a PR to master. Require successful relevant CI, including canonical bundle and native pair, before merge. Do not merge unrelated failing draft PR #413.
3. On the exact merged master, require Native Entity Retirement and canonical 45-addon bundle success, then the automatic full-stack follower triggered by that exact bundle run. Manual full-stack dispatch currently selects the published release bundle and is unsuitable here.
4. Run Reproducible Release with **publish=false** on that exact master. Preserve every full-source/full-JAR/full-ZIP evidence comparison. Verify all three proposed assets and save the canonical r143 bundle, superseding the outdated r140 handoff.
5. Update release tracker [#378](https://github.com/wickidcow/Slimefun-Legacy/issues/378) and the Networks completion handoff with concrete commit/run/artifact evidence. Request core publication approval only when the verified release is ready.
