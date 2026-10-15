# r137 Black Market validation candidate - not a release

## Scope

Stage coordinated validation of `wickidcow/SF_MagicExpansion#18` at exact source `3a8818528cf32701d19c99fc33fa7f7ef2545be4`. This adds missing-cycle receipt preservation, strict state reads, failed-initialization invalidation and stale-refresh protection to the candidate addon selection. It does not diagnose or repair Albion's original changed-cycle incident.

The base is Slimefun Legacy `c72fc1699934846bf25277c37640023b55aeb022`. Only MagicExpansion's addon source pin and the candidate bundle revision change. Networks remains at `bcdef34d362dc74aa1aab23c8961a629daa79950`; all 44 non-MagicExpansion addon entries, the 45-addon roster, exclusions and compatibility policy remain unchanged. No core Java, plugin version, workflow, resource pack or published asset is modified by this staging commit.

## Provenance and validation

- Original matrix Git blob: `adcbf8c36eda42e2c73fd75d1a9c2f0ce1915ed4`.
- Candidate matrix Git blob: `29f26fb46d9afacfc2e4db92a4ff93473bf82b28`.
- Local JSON/semantic validation confirms 45 unique repositories, 40-character exact source pins, one changed addon entry, 44 identical non-MagicExpansion entries and unchanged exclusions/policy.
- MagicExpansion exact-source workflow `38659745872` completed successfully. Its PR records 146 executed tests including 40 Black Market tests; these source checks are not substituted for the coordinated stack results.
- The existing pull-request workflows must build the exact 45-addon selection and exercise the full-stack clean boot/restart checks on Paper 1.21.11, 26.2, 26.3 and the configured experimental Purpur 26.3 target. Record exact-head job results, artifacts and any skipped dependency gates before calling this validation complete.
- The existing native Networks/Fluffy conservation probe remains in the 26.3 full-stack job. It is not a Black Market purchase/restart probe.

## Publication boundary

This matrix is for an isolated draft PR and CI artifacts only. The candidate MagicExpansion source still declares version 1.1.12; it is NOT the published 1.1.12 release JAR. Identify it by exact source commit and checksum. Do not install an ambiguously versioned CI JAR on production or replace the public r136 ZIP with this archive.

Keep Slimefun 4.1.74, r136, published Networks 1.0.55, published MagicExpansion 1.1.12 and resource-pack assets unchanged. Do not merge this candidate, dispatch publishing workflows or release assets as part of validation. A later reviewed publication needs a distinct MagicExpansion release version, exact released-source pins, revalidation and checksum verification. An addon-only refresh must preserve the other 44 physical published JARs, not merely their source pins. This source-built CI bundle does not establish that byte-identity guarantee.

The core used by coordinated CI is the current branch candidate, not a claim that it is byte-identical to the published 4.1.74 JAR. Production-core and copied-world validation remain separate.

## Remaining production evidence

Albion's current read-only `/magicexpansion blackmarket status` output and a stopped-server consistent copy of `black_market/cycle.yml` plus `black_market/players/` have not been examined. No automatic repair, receipt reset, file deletion, forced unlock, cross-process locking or crash-atomicity claim is introduced. Preserve originals; reconcile only on a disposable copy before any recovery decision.
