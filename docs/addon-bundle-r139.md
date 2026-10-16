## Addon ZIP refresh r139 — Networks 1.0.57

The Slimefun Legacy **4.1.74** addon bundle advances from r138 to **r139** by replacing only Networks **1.0.55** with the published **Networks 1.0.57** JAR. MagicExpansion remains **1.1.15** from r138 and the other **43 addon JARs are byte-for-byte unchanged**. The Slimefun Legacy 4.1.74 core and optional resource pack are unchanged.

The revision-specific file is `SF_Addons_r139_1.21.11-26.3.zip`. The r138 file remains available as `SF_Addons_r138_1.21.11-26.3.zip`; the revisionless addon ZIP is maintained only as a compatibility alias for existing links.

Networks 1.0.57 is source commit `f5486918ab7e115298b453dc23e26a2225aedaba`, JAR SHA-256 `125a54605244f3ecaa2d873cca4dff7a78ff7772a445ad5d6f4c38f3603d57ab`. It retains the 1.0.56 Dust Extractor source-change compensation safety net and adds controller integrity, manual-crafter atomicity, Auto Crafter read-side batching, and full-line transfer traversal reuse. Item IDs, recipes, storage formats, default transfer budgets, Quantum routing order, and empty-Quantum assignment policy are unchanged.

The r139 gate starts from the exact r138 candidate SHA-256 `f0870efbe26f007d7c95d419c7ba112875492ef75520c23052aca6ec6fd18419`. Publication is refused unless the live r138 release asset later has that same digest. It boots the exact 45-addon r139 ZIP twice on Paper 1.21.11, Paper 26.2, Paper 26.3 and Purpur 26.3, runs Black Market four-JVM receipt persistence on every lane, and runs the real Networks/Fluffy conservation probe on Paper 26.3.

InfinityExpansion2 2.0.14 is being validated separately to eliminate the asynchronous Dust Extractor producer race itself. r139 does not silently substitute an unreleased IE2 candidate; Networks 1.0.57 remains loss-safe if another producer changes a source concurrently.
