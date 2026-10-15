# Networks-only addon bundle r139 — integration candidate, not published

This selection replaces only Networks 1.0.55 with the published 1.0.56 release at
`c0b388e45e929c1a721d7a8aa968b2e0d4fc10e9`. It retains all 44 other r137 addon
source pins. r138 remains reserved for separate MagicExpansion work; this is not
permission to replace a newer published selection with the old r137 baseline.

The separately prepared exact-byte ZIP is
`541708ca969bb6d6c7a0b11510e856b221c2dbd984e6523404a53ebdaa60ff1c`.
Its Networks JAR is
`25a1bbeef780bb3d263506892df3b8b8cb42ec3be5ee5d36393c8fe1e7c52d89`.
All 44 other JARs are byte-identical to published r137. The published Slimefun
4.1.74 core and resource pack are unchanged. A source-rebuilt CI bundle is not
silently substituted for this exact tested ZIP.

Exact-byte native validation is tracked at
https://github.com/wickidcow/Slimefun-Legacy/actions/runs/38823000873 . Check its
actual completed outcome and retained evidence before publication; this note
alone does not assert a successful workflow. The fixture boots the entire
selection twice on Paper 1.21.11/26.2/26.3 and experimental Purpur 26.3, checks
real Networks/Fluffy conservation on Paper 26.3, and checks Black Market receipts
across four JVM phases on each platform. It is not a live-world or crash proof.

The inherited r137 exact-byte workflow is historical and now manual-only: its
lease refers to the pre-r137 published asset roster and cannot validate a newer
bundle. Its assertions are retained. New r139 admission tests run independently
alongside the existing source-bundle and full-stack workflows; no guard is
removed from the runtime code. The new tests use the exact Networks release,
synthetic unrelated plugin bytes and a mocked compiler; they never start Java.

No item IDs, recipes, production rates, plugin production source, serialization
formats, core release identity or live server data are changed in this PR.
The original Infinity Dust Extractor source mutation remains unexplained;
Networks 1.0.56 fixes destructive VOID cleanup, not every possible source conflict.

Before publication, finish exact-head integration checks, verify the frozen
candidate/native evidence, recheck master and current release asset leases,
reconcile concurrent core/MagicExpansion work, and obtain the required approval.
Keep the previous published ZIP as a rollback copy. Never overwrite the published
core/resource-pack files or install all optional addons indiscriminately.
