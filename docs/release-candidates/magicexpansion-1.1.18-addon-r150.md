# MagicExpansion 1.1.18 — coordinated Slimefun addon bundle r150

**Scope:** Replace only MagicExpansion **1.1.17 → 1.1.18** in the 45-addon `SF_Addons_1.21.11-26.3.zip`. The core Slimefun JAR, Java resource pack, and all Geyser-owned content are outside this update.

The fixed addon source is the merged `wickidcow/SF_MagicExpansion` commit `7c2c1a927176ebd0aaab4481dcc21a51320f7f10` ([PR #27](https://github.com/wickidcow/SF_MagicExpansion/pull/27)). It reserves all **54 inventory slots** for the Diamond Mining Robot/resource machines and rejects an undersized legacy menu instead of producing repeated `Index 18 out of bounds for length 18` ticker errors. The fix preserves machine outputs and existing game data. The canonical MagicExpansion 1.1.18 build and four-platform resource-machine runtime validations completed successfully before this bundle update.

## Version and preservation contract

- **Input:** the live GitHub release's fully verified canonical **r149** ZIP (the v4.1.76 r149 ZIP was SHA-256 `08e520b68a40896c09773f8b831c47130a05cb1b01e1f1ab573ca58064ad445e`).
- **Output:** the same named ZIP, manifest revision **r150**, exactly **45** installable addon JARs.
- **Only changed addon:** MagicExpansion from `SF_MagicExpansion1.1.17.jar` to `SF_MagicExpansion1.1.18.jar`, exact merged source `7c2c1a927176ebd0aaab4481dcc21a51320f7f10`.
- **Unchanged:** the 44 other addon JARs byte-for-byte, especially Networks **1.0.61**, SlimeHUD **2.0.7**, and InfinityExpansion2 **2.0.15**.
- **Metadata:** update `SF_ADDON_MANIFEST.json`, `SHA256SUMS.txt`, and retained source pin; preserve core source provenance.
- **Distribution:** the r150 Actions preview is not a published release; only the checksum/backup/rollback guarded publisher can replace the live asset once exact merged-source canonical and four-target full-stack gates succeed.

The publication workflow can use the latest **v4.1.76** or **v4.1.77** release only when its existing ZIP is verified to be the exact r149 input. It fails closed if the live release or asset changes while the process is running. It does **not** change the Slimefun Legacy core JAR or any resource pack.

## Testing after deployment

Back up the full server and stop it normally. Install only the JARs needed by the server, remove the previous MagicExpansion JAR, and restart without `/reload`. A Diamond Mining Robot should open directly as a 54-slot menu and complete its operation without the repeated 18-slot inventory error.
