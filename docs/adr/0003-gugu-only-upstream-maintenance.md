# ADR 0003: GuGu is the sole maintained upstream

- Status: Accepted
- Date: 2026-10-17
- Supersedes: [ADR 0002](0002-reviewed-multi-fork-upstream-intake.md) for future upstream intake

## Decision

GuGu (`SlimefunGuguProject/Slimefun4`) is the only external Slimefun core tracked for future maintenance, source intake and API drift checks. Slimefun Legacy remains the runtime and release target. United and the other former reference forks are removed from active polling and CI source-probe targets. Their unimplemented roadmap candidates are retired.

GuGu changes still require explicit review, health gates, English-language review, protected API checks, saved-data checks and maintained-addon validation. No upstream change is automatically merged or substituted into the source tree. Paper, Purpur and Folia are server platforms; their version and scheduler validation continues independently of this upstream policy.

## Existing data and addon contracts

Historical core identifiers remain valid in existing addon declarations. The public enum values, existing API facade identifiers, compatibility method descriptors, saved-item readers and source attribution remain intact. These identifiers describe established addon/API history; they do not promise new upstream maintenance or current cross-fork runtime certification.

Original Slimefun is retained as a historical API and data reference without polling its current branch. Implemented-feature source records and dated audit results retain their provenance. Old release assets and historical evidence are not rewritten.

## Enforcement

`compatibility/upstream-sources.json` lists only GuGu as an active source. `compatibility/cross-fork-api-matrix.json` emits only the GuGu advisory probe. Their validators reject additional active forks or a substituted repository before a remote poll or CI target is produced. Focused tests exercise both selection paths and are part of the mandatory Legacy verifier.

The previous stable Legacy API and maintained-addon regression gates remain release blocking. A source-marker probe is advisory evidence, not a binary or saved-world compatibility guarantee.
