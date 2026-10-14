## Addon bundle refresh — revision 136

The addon ZIP for Slimefun Legacy **4.1.74** is updated to **r136**, with exactly two replacements among 45 maintained addons:

| Addon | Previous r135 | r136 |
| --- | --- | --- |
| Networks | 1.0.54 | **1.0.55** |
| MagicExpansion | 1.1.11 | **1.1.12** |

**The other 43 JARs are byte-for-byte unchanged. The Slimefun-Legacy4.1.74.jar core and SlimefunLegacyRP.zip resource pack are unchanged.** Existing bundle exclusions, the Minecraft 1.21.11 minimum, item IDs, stored data and configuration remain unchanged.

Networks 1.0.55 prevents a directional line transfer from depositing items back into the same physical storage block supplying them. It retains source-identity verification and compensation for other inventory changes. MagicExpansion 1.1.12 adds the OP-only `/magicexpansion blackmarket status` command and correctly reports an effective lock when the cycle marker has changed. This is read-only diagnostics: it does **not** reset receipts, reroll offers, or repair/unlock an existing Black Market file mismatch.

### Verification and provenance

The selected source trees passed the full 45-addon build (run 38598879430), cross-version full-stack checks (run 38598879446), and a non-skipped Paper 26.3 Networks/Fluffy conservation probe. The independent addon release builds are checked again before this archive is published.

The source manifest retains its exact CI-tested source locks. The official release merge commits are checked to have **identical Git trees**, and both identities are recorded in the release validation report and `COMPATIBILITY.txt`:

- Networks tested source `bcdef34d362dc74aa1aab23c8961a629daa79950`; release merge `56b447a535502c0f82bc94e0d734e8d4aad85f9f`.
- MagicExpansion tested source `144d973a014ce943e4e9173ea17f7bf31ed00fa3`; release merge `7a33360bf19a1a82e7874025f6e8f196938b3c7b`.

Publication uses the exact released r135 input SHA-256 `dd0f8e3dc952acbd2dcf78f1bc85a5c1592b6ef2adf0d0c9af88fb45a40078f1`. It verifies official addon tags, downloaded JAR digests, Java 21 bytecode, descriptor versions, every ZIP checksum, deterministic reconstruction, and all 43 unchanged JAR byte streams. A live-release identity check prevents knowingly overwriting a newer bundle or changing core/RP assets. The old ZIP is retained until the replacement's public download verifies; a rollback copy and the validation report are retained in Actions artifacts.

### Installation

Stop the server, back up worlds and plugin data, replace the older Networks and MagicExpansion JARs rather than loading duplicates, and start normally. Do not use `/reload`. Keep `plugins/magicexpansion/black_market/` and its player receipts intact. Inspect the logged directional-line inventories and use `/magicexpansion blackmarket status` for the existing market issue.

No live Albion files were modified during release. Automated tests cover the stated disposable-server cases, not every historical world, third-party storage integration, or power-loss scenario; this release is not a claim of universal duplication prevention. Continue normal backup-based validation before deploying to production.
