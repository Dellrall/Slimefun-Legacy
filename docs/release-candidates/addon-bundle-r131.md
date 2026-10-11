# Canonical addon bundle r131 — FNAmplifications Gem Unbinder drag safety

This development bundle advances canonical revision **130 → 131** without changing the
bundle filename, 45-member roster, supported Minecraft floor, excluded addons, storage
formats, or migration policy. It is stacked on the 4.1.74 compatibility-hardening work
and is **not** a replacement for the published Slimefun Legacy 4.1.73 assets.

## Exact source change

Only one of the 45 fixed source pins changes:

| Addon | Previous r130 pin | r131 pin | Published release |
| --- | --- | --- | --- |
| FNAmplifications | `2eb07e7bca82d4d7621224e6f9e4942481e7e8f7` | `24856fcb4efabb4edf900bf5d3e6a23cb9ba827f` | [4.2.8](https://github.com/wickidcow/SF_FNAmplifications/releases/tag/v4.2.8) |

The new pin is a strict descendant of the r130 pin. The published 4.2.8 release points
to the exact r131 commit. Its raw JAR is **521,974 bytes**, SHA-256
`06ecc5824c9a295e44c282370e0d11c3c388013c2ff25c8bc34cf43c43a7b21f`, identical
to the successful default-branch CI artifact.

The other **44 addon source pins remain byte-for-byte unchanged in the matrix**.

## FNAmplifications behavior

FNAmplifications 4.2.8 prevents an `InventoryDragEvent` from inserting player-owned
stacks into the temporary Gem Unbinder selector whenever any dragged raw slot belongs
to its top inventory. Drags entirely inside the player inventory remain allowed.

The update preserves existing click cancellation, unbind-chance validation, stale
item/tool rejection, gem metadata handling, recipes and item IDs, and the established
whole-stack unbinder cost for an accepted attempt. It introduces no saved-data or
storage migration.

The addon also updates its Slimefun United CI bootstrap to use United's checked-in
Maven wrapper (3.9.8) instead of the runner's Maven 3.10.0, whose removed
`MessageUtils` class is incompatible with United's git-versioning extension. Both
Legacy and United compatibility jobs passed before publication.

## Required integration gates

Before r131 may become the canonical development bundle:

- build the exact 45 fixed source pins;
- verify addon descriptors, names, Java 21 bytecode and archive checksums;
- require FNAmplifications 4.2.8 at the exact published commit;
- run the full Paper 1.21.11, Paper 26.2, Paper 26.3 and experimental Purpur 26.3
  two-boot stack with all 45 addons enabled;
- preserve the existing Networks 1.0.50 and InfinityExpansion2 2.0.13 pins and their
  storage/order regression coverage;
- do not publish or overwrite Slimefun Legacy 4.1.73 as part of this bundle-only step.

The ABI-hardening PR underneath this stacked candidate must be merged and the r131 PR
retargeted to current `master` before final integration.
