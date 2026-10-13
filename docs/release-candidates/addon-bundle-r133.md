# Canonical Slimefun Legacy addon bundle r133 — Networks 1.0.53 security refresh

## Scope

Advance the already-selected **r132 candidate matrix** to **r133** by changing only
`wickidcow/SF_NetworksExp` from Networks **1.0.52** at source
`e89ab7da8a2d963db3f987a5c4ccb21626f69b1e` to the merged,
released **1.0.53** source
`cda18edd882194607d7fd65b8815afdedad52abc`.

The other **44 exact source pins in r132** are unchanged. This includes the
separately approved **FNAmplifications 4.2.8** update already staged in r132.
**Important:** the *currently published* Slimefun Legacy v4.1.73 ZIP is still
r131 with Networks 1.0.52, so comparing r133 to that published ZIP will reflect
both the previously staged r132 FNAmplifications selection and this r133 Networks
selection. Do not misrepresent this as a single-JAR difference versus the
published r131 asset.

## Networks updates

- Prevent item duplication after a partially successful transfer followed by
  an exception by reconciling actual accepted quantities.
- Reject stale Quantum item identity and guard quantity changes with
  storage-scoped synchronization.
- Protect tick versus break / reassignment and manual Quick Insert or Extract
  transactions; recover cold storage after reboot.
- Preserve all 289 maintained Networks item IDs, menus, recipes and persistent
  storage format. No conversion or reset is required.

## Release evidence

- [Networks 1.0.53 release](https://github.com/wickidcow/SF_NetworksExp/releases/tag/v1.0.53),
  official raw JAR `SF_Networks1.0.53.jar` SHA-256
  `ebf6a5fc082b56626459ba6af36f0938d084b2a42cc0ea71dac8508facb08cd9`.
- [Three-core and Java-21 universal release CI](https://github.com/wickidcow/SF_NetworksExp/actions/runs/38425384723):
  succeeded on merged source, including the native Purpur 1.21.11
  manager/viewer and two-JVM persisted Quantum Storage tests.
- [Native Paper 26.3 CI](https://github.com/wickidcow/SF_NetworksExp/actions/runs/38424480975):
  all seven candidate gates passed, including two full Minecraft process
  restarts, physical-block break and exact PDC/item-count conservation.
- Future *live* `/sf tick top` comparisons must use similar loaded chunks and
  machine activity. A previous October 7 sample showed Networks at **1.45ms
  for 1,874 blocks** out of 23.67ms total; this was **before 1.0.53**, and is not
  a claim of a measured 1.0.53 performance improvement.

## Publication gates

1. Build all **45 exact source-pinned addons** from the revision-133 matrix
   against verified Slimefun Legacy 4.1.73 and the maintained Paper 26.3 API.
2. Check 1.21.11 Java-21 bytecode floor, exact plugin IDs, registered items,
   no missing optional providers, and preservation of the other 44 r132 pins.
3. Run clean-start and restart smoke on supported servers with the canonical
   candidate ZIP, and confirm no startup errors.
4. Publish to v4.1.73 only after candidate bundle verification and SHA-256
   verification. Do not rewrite any core JAR, resource-pack asset or unrelated
   addon entry.

The exact third-party server-owner duplication report remains unconfirmed.
These updates significantly strengthen integrity but must not be described
as a guarantee against every possible plugin interaction or item dupe.
