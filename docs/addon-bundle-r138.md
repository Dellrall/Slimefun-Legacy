## Addon ZIP refresh r138 — MagicExpansion 1.1.15

The canonical `SF_Addons_1.21.11-26.3.zip` for Slimefun Legacy **4.1.74** advances from revision **137** to **138**. Only MagicExpansion changes: the bundle moves from **1.1.13** directly to **1.1.15**. The other **44 addon JARs remain byte-for-byte identical to published r137**. The Slimefun Legacy 4.1.74 core JAR and optional resource pack are unchanged.

MagicExpansion 1.1.15 repairs the **SF Timings Machine / Slimefun Tick Monitor**. Loaded monitors request a shared detailed profiler sample automatically instead of displaying zero until an operator runs `/sf tick top`. Automatic requests are shared and rate-limited, missing or stale samples are explicit, genuine measured zeroes remain valid, and the display now distinguishes **Slimefun total** from **This chunk**. Existing item IDs, recipe, block storage, hologram positions, Black Market data and fishing behavior are preserved.

The published MagicExpansion 1.1.15 JAR is source commit `9443393b3ef5f0982194d9084eaed91d7d820dca` with SHA-256 `46c01290c54d918c39e8bb0f58d3ce135e2143c86b0f45858245f78fcafeeaad`. Its release build passed 165 tests with zero failures/errors/skips, including 15 Tick Monitor sampling regressions, and the complete 45-addon stack passed on Paper 1.21.11, Paper 26.2, Paper 26.3 and Purpur 26.3.

The r138 publication gate additionally reconstructs the bundle from the currently published r137 ZIP, proves all 44 unrelated JAR byte streams are unchanged, boots the exact refreshed 45-addon archive twice on all four runtime lanes, and re-runs the native Networks/Fluffy conservation probe on Paper 26.3. Publication is refused if the live core, resource pack or r137 bundle changes while validation is running.

The previous r137 canonical ZIP is retained as `SF_Addons_r137_1.21.11-26.3.zip` for rollback. Stop the server and back up worlds/plugin data before replacing JARs. Remove the older MagicExpansion JAR, install only one version, and start normally rather than using `/reload`.

The archived r137 candidate workflow is revision-gated, so advancing the maintained matrix to r138 skips obsolete r137 reconstruction instead of reporting a false release failure.
