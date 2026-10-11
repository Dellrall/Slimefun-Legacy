# Canonical addon bundle r130 — coordinated latest stable refresh

This source candidate advances canonical bundle revision **129 → 130** without altering
the bundle filename, 45-member roster, API support floor, archive policy, or excluded addons.
It pairs with Slimefun Legacy **4.1.73** (unpublished until all gated checks complete).

## Updated exact-source pins

| Addon | Published stable version | Old pinned commit | New pinned commit |
| --- | --- | --- | --- |
| [SF_BetterChests](https://github.com/wickidcow/SF_BetterChests/releases/tag/v1.0.3) | `1.0.3` | `5c830e845d2849e0d8aea53414be8cba80af6775` | `51fd6616d8ad6d8a6153237d5274235f61a6f277` |
| [SF_BuildingStaff](https://github.com/wickidcow/SF_BuildingStaff/releases/tag/v1.0.35) | `1.0.35` | `9f017f4ca4cec5997c14ccd1e564a21b21ed16a0` | `290c14bc4822c81598a267b7191731bcf5f23a0b` |
| [SF_InfinityExpansion2](https://github.com/wickidcow/SF_InfinityExpansion2/releases/tag/v2.0.13) | `2.0.13` | `a66a534406bf81222549458213313816dbdfb98f` | `c9ad8394ee65e5577c3e031e24b562a8a7b2d0f5` |
| [SF_NetworksExp](https://github.com/wickidcow/SF_NetworksExp/releases/tag/v1.0.50) | `1.0.50` | `839a66c39a355371ea17ecafd29366d1de0b872e` | `c320adcaec21b945b25e33b303a42ea18007a7fb` |
| [SF_RykenSlimeCustomizer](https://github.com/wickidcow/SF_RykenSlimeCustomizer/releases/tag/v3.1.11) | `3.1.11` | `9fc2dc5f9cf3bf650602b70095da44a57f42172b` | `e62b10423a64d1940ee4bc87947e2ff42b0ee3df` |
| [SF_SlimeTinkerIE2](https://github.com/wickidcow/SF_SlimeTinkerIE2/releases/tag/v2.0.7) | `2.0.7` | `bdb2ba51ad946de686c50dc1745ba89053b4535d` | `bfb072fedb9f9135a27a93483d69da2bcdfb927a` |
| [SF_Supreme](https://github.com/wickidcow/SF_Supreme/releases/tag/v1.0.20) | `1.0.20` | `118eb72e84a9975681805749447d436a26b40103` | `ed79026880b127d40d24cfe6b9fcabc2888e9562` |

All seven selected release tags resolve to the new commit SHA shown above. These are
published, non-prerelease JAR versions. The remaining **38 members retain their existing
newer-or-equal source pins**; don't roll them back to older tags or replace them blindly
with unreviewed default-branch commits. The 45-member bundle must always be generated
from this exact-source matrix, not assembled by mixing arbitrary downloaded JARs.

## Compatibility and data safety

- Preserve 1.21.11 minimum, Paper/Purpur 26.2 compatibility, and 26.3 primary API target.
- Maintain Java 21 bytecode output and Java 25 26.x server/build verification.
- No automatic migrations, saved storage rewrites, machine/item ID changes, or edits to
  already-published v4.1.72 artifacts.
- Keep SF_Magic8Ball integrated into core, SF_DracFun excluded in favor of
  SF_DracFun2, and SF_Magic_RSC out of the canonical bundle.
- The 4.1.73 core fixes the event-listener ABI linkage error on Purpur 1.21.11.
  Beacon Plus is a trigger of the original listener error, not a separate broken addon.
- New Networks storage/drawer discovery and InfinityExpansion2 mob-card guide behavior
  require targeted runtime regression checking as well as normal boot activation.

## Validation required before publication

The source update and tag audit are not a passing bundle build.
Require the candidate core build/tests, API compatibility checks, Paper/Purpur 1.21.11
runtime and bytecode guard, Paper/Purpur 26.2 and Paper/Purpur 26.3 lanes where
supported, required addon compatibility, a **45/45 exact-source r130 bundle**,
two-boot full-stack smoke checks, plugin identities, checksums, and reproducible
release verification. Report any failures without bypassing release gates.

Do not replace the published 4.1.72 release; the first eligible coordinated
release name is **v4.1.73**. Publish only from the existing gated Reproducible
Release workflow after verifying exact-source provenance and release notes.
