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
- Final merged-master native, canonical-bundle, exact full-stack and reproducible release gates: **pending**. Earlier r142 runs and addon release tests do not substitute for the exact new candidate.

### PR #414 hosted acceptance and current blocker

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

## Changed files and branch

Working branch: `release/4.1.76-network-pair-r143`, based on `1cb32d6e95b305998065b8ef6b936a56f679187d`. Implementation commit: `660e0aa53a676b507095a24883d12f327ffa824a`. Integration PR: [#414](https://github.com/wickidcow/Slimefun-Legacy/pull/414), open and ready for review; final GitHub gates are pending. Local verification and bounded independent reviews passed.

Files: canonical matrix, `gradle.properties`, README, `docs/releases/4.1.76.md`, this checkpoint; canonical bundle/native/reproducible workflows; published-pair staging helper and rejection tests; paired fixture lock/runner and contract tests; r135 and Black Market fixtures and native contract tests; release evidence synthetic fixtures and dispatch controls; root documentation allowlist for the required checkpoint; `scripts/compile_addon_paper_26_3.py` and its real Gradle routing regression. Production Java remains unchanged.

## Exact next actions

1. **Local verification complete:** full build, invariants and 548 normal/optimized Python controls passed; production Java is unchanged.
2. The narrow RykenSlimeCustomizer dependency-routing repair and actual pinned compile are verified. Follow PR #414 CI on its latest head, including the repair and this checkpoint. Require successful relevant CI, including canonical bundle and native pair, before merging to master. Do not merge unrelated failing draft PR #413.
3. On the exact merged master, require Native Entity Retirement and canonical 45-addon bundle success, then the automatic full-stack follower triggered by that exact bundle run. Manual full-stack dispatch currently selects the published release bundle and is unsuitable here.
4. Run Reproducible Release with **publish=false** on that exact master. Preserve every full-source/full-JAR/full-ZIP evidence comparison. Verify all three proposed assets and save the canonical r143 bundle, superseding the outdated r140 handoff.
5. Update release tracker [#378](https://github.com/wickidcow/Slimefun-Legacy/issues/378) and the Networks completion handoff with concrete commit/run/artifact evidence. Request core publication approval only when the verified release is ready.
