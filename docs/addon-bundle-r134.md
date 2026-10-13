## Addon bundle refresh — revision 134

This is the coordinated, exact-source update of the published
`SF_Addons_1.21.11-26.3.zip` for the existing **Slimefun Legacy 4.1.73**
core. It begins with the verified published revision-133 ZIP
(SHA-256 `6dc5dfa680a86640ff70558966c1d413940e9f745de75e1911ef07f0e35dcd1e`)
and replaces **exactly three of 45 maintained addon JARs**.

| Addon | Previously bundled | Revision 134 | Released artifact SHA-256 |
| --- | --- | --- | --- |
| Networks | 1.0.52 | **1.0.53** | `ebf6a5fc082b56626459ba6af36f0938d084b2a42cc0ea71dac8508facb08cd9` |
| Magic Expansion | 1.1.9 | **1.1.11** | `cf2d2481d5e965e0eedbfcd1a3432abcc58d9fbd7a4ab475b5a14d8e40e7d9a5` |
| Lucky Blocks | 1.0.4 | **1.0.5** | `fa228deab333047a7f52f5cf21f83711a3e439d226e6a76ccfdb02b241b06341` |

**All other 42 addon JARs remain byte-for-byte unchanged**, including the
previously published Supreme 1.0.20 Soulbound and armor-effects rebuild,
FNAmplifications 4.2.8 Gem Unbinder drag protection, and all existing
configuration and resource-pack assets. The 45-addon roster and the Slimefun
core JAR remain unchanged.

### Changes and evidence

**Networks 1.0.53:** [official release](https://github.com/wickidcow/SF_NetworksExp/releases/tag/v1.0.53).
Hardens source quantity reconciliation after partially failed deposits,
live Quantum Storage identity checks, per-cache transactions, manual
extraction and tick/break races. Native Paper 26.3 and Purpur 1.21.11 checks
passed, including saved custom-item and output counts across **two distinct
Java server processes**. Preserves registered item IDs, recipes and persistent
storage structures.

**Magic Expansion 1.1.11:**
[official release](https://github.com/wickidcow/SF_MagicExpansion/releases/tag/v1.1.11).
Includes the 1.1.10 Black Market persistence / purchase-receipt protection
and the additional coordinate-safe rare fishing notices. Public rare/super
rare/Fish Emperor messages are **off by default**, including for old config
files; publicly announcing player world/X/Y/Z requires explicit opt-in to
both `fishing.announcements.enabled` and
`fishing.announcements.show-coordinates`. Private congrats can remain on.
Existing catches, rewards, fish metadata, research and shop item IDs remain.

**Lucky Blocks 1.0.5:**
[official release](https://github.com/wickidcow/SF_LuckyBlocks/releases/tag/v1.0.5).
Adds the OP-only `/luckygive` command with permission and tab-completion
checks, full-inventory protection and Folia-safe delivery. The restored
historical lucky armor/weapons and other existing rewards are retained.

### Release controls

1. Require the exact published revision-133 input archive, Slimefun 4.1.73
   core hash and optional resource-pack hash to match independently verified
   values; refuse publication if any has changed.
2. Download the three official release JARs; require exact file names,
   plugin descriptor versions, SHA-256 hashes and Java 21 compatible bytecode.
3. Use the existing archive-preserving, targeted `refresh_release_addon.py`
   routine **three times** with intermediate source matrices, then confirm
   the final 45-member manifest equals this exact revision-134 source matrix.
4. Verify no duplicate JAR names, exactly **42 unchanged JAR byte streams**,
   no unrelated ZIP members changed, internal JAR hashes valid, and two
   independently produced ZIPs are SHA-256-identical.
5. Run canonical 45-addon compilation and full-stack tests covering
   Minecraft 1.21.11 and Paper/Purpur 26.3. Publication is fail-closed if
   any required release gate fails.
6. Replace only the v4.1.73 addon ZIP after comparing the live release lease;
   do **not** overwrite the already-approved core JAR or resource pack.

### Installation

On a staging server, stop Minecraft, back up the world and plugin data,
replace older Networks, Magic Expansion and Lucky Blocks JARs rather than
running duplicate versions, then start the server normally. Do not use
`/reload`. In particular, protect `plugins/magicexpansion/black_market/`
because it now holds durable purchase receipts. Check the logs for
loading/linkage errors and test storage counts, one lucky give and the
privacy-default fishing messages before deployment on a busy production server.

These tests reduce known duplication risks but do not prove that every
third-party storage or crash/power-loss interleaving is safe.
