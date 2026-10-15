# r137 native Black Market receipt/restart gate

This is a test-only follow-up to Slimefun Legacy PR #386. It does not change any addon source pin, version, core Java, item format, live server data or published asset. MagicExpansion source remains `3a8818528cf32701d19c99fc33fa7f7ef2545be4`; its candidate descriptor still says 1.1.12, not a distinct published replacement.

## Executed locally

The 18 offline Python admission tests pass. They exercise synthetic manifests and bytes, not actual JAR execution. The original full-stack workflow was reconstructed and Git-blob verified as `617f408f1dae09643958b460eb8a38993c1ceebd` before narrow additions. YAML parses; read-only Actions/contents permissions and the existing four runtime lanes are retained.

## Native gate added, not yet claimed passed

The existing full-stack workflow now compiles and runs a non-shipping plugin using the installed MagicExpansion classloader and its actual BlackMarketFileStore. No duplicate store implementation or mocked Bukkit is used in this native probe.

Each Paper 1.21.11/26.2/26.3 lane and experimental pinned Purpur 26.3 lane must complete four additional clean JVM boots after its original two-boot smoke:

1. Seed ten varied synthetic offers, costs, purchase/reveal receipts and named/lore/PDC-bearing items; retain baseline bytes.
2. Read the same records after restart, preserving bytes and item identities; test external-cycle rewrite refusal and failed initialization invalidation.
3. Restart with only the synthetic cycle marker moved aside while stopped. Require refusal without creating a cycle or changing receipts.
4. Restore the exact synthetic marker while stopped and restart. Require the same receipts and offers; then exercise legitimate rotation and stale refresh refusal.

Admission requires the exact r137 MagicExpansion pin, 45 unique addon repositories/JARs, every manifest/bundle/staged JAR SHA-256, a passing full-stack fixture, offline generated-world settings and real non-symlink fixture directories. The runner binds its admitted server to loopback. The Java probe additionally requires a nonce authorization file, the matching JVM property, zero players, a console command and the server thread. It operates only on its own synthetic-ledger directory, never MagicExpansion's real black_market directory.

Every phase requires fresh evidence tied to phase, nonce and PID, a PASS console marker and normal process exit. Server, core and addon hashes are checked across boots. Logs, compilation output and result JSON are retained even on runtime failure. Existing native Networks/Fluffy conservation remains required on Paper 26.3. No failed or skipped native stage may be reported as successful.

## Release boundary

This gate tests actual store serialization with a native server in the coordinated addon environment. It is not a client-click transaction test, crash/power-loss atomicity proof, historical-world upgrade test, live market repair, or diagnosis of Albion's original externally changed cycle.yml. Synthetic marker restoration is not a production recovery instruction.

Keep PR #18 and #386 unreleased until exact-head coordinated results are inspected. A later release requires a distinct MagicExpansion version, final source pins, renewed checks and preservation of the other 44 published physical JARs. Do not publish this test plugin or include it in the addon ZIP.
