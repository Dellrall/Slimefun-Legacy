# Canonical addon bundle r132 — FNAmplifications drag safety

Advance the development bundle from r131 to r132 by selecting the released
FNAmplifications 4.2.8 fix. This resumes the bundle work from closed PR #369 on
current master; r131 has since been used by the published Networks 1.0.52 refresh.

## Source selection

| Addon | r131 source | r132 source |
| --- | --- | --- |
| FNAmplifications | `2eb07e7bca82d4d7621224e6f9e4942481e7e8f7` | `24856fcb4efabb4edf900bf5d3e6a23cb9ba827f` |

The other 44 source pins are unchanged, including Networks 1.0.52 at
`e89ab7da8a2d963db3f987a5c4ccb21626f69b1e` and InfinityExpansion2 2.0.13 at
`c9ad8394ee65e5577c3e031e24b562a8a7b2d0f5`. The 45-addon roster, exclusions,
Minecraft 1.21.11 floor and Java 21 bytecode policy remain unchanged.

## Player behavior

FNAmplifications 4.2.8 cancels inventory drags touching the temporary Gem Unbinder
selector. Drags entirely within the player's inventory remain allowed. Item IDs,
recipes, gem metadata, click handling, unbind chances and accepted-attempt tool
costs retain their existing behavior. No storage migration is introduced.

## Evidence and remaining gates

- The [addon release](https://github.com/wickidcow/SF_FNAmplifications/releases/tag/v4.2.8)
  targets the exact selected source commit.
- [Default-branch CI](https://github.com/wickidcow/SF_FNAmplifications/actions/runs/38152097441)
  passed its Legacy and United compatibility jobs and release job.
- GitHub reports `SF_FNAmplifications4.2.8.jar` as 521,974 bytes with SHA-256
  `06ecc5824c9a295e44c282370e0d11c3c388013c2ff25c8bc34cf43c43a7b21f`.
- Local matrix comparison confirms that only FNAmplifications changes.

The candidate still requires the exact-source canonical bundle build, archive and
bytecode checks, and all-45-addon double-boot runtime gates. Addon CI results do not
replace those integration gates or certify arbitrary player worlds. The historical
maintained-addon test ledger retains its original evidence attribution.

This selection change does not bump the core version or publish/replace the
Slimefun Legacy 4.1.73 release assets. The whole-JAR platform linkage hardening
continues separately in PR #368.
