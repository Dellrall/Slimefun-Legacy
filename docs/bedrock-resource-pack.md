# Optional Bedrock resource pack — Geyser required

The Slimefun Legacy 4.1.76 candidate includes an **optional, experimental resource
pack bundle for Bedrock players**:
[`SFL_GEYSER_RP_experimental_v1.0.3_complete.zip`](../compatibility/bedrock/SFL_GEYSER_RP_experimental_v1.0.3_complete.zip).
**Geyser must be installed and configured. Install both main `.mcpack` files and
all 23 matching JSON mappings together in the running Geyser instance.** These
are drop-in resource and mapping files; the ZIP includes no Geyser plugin JAR or
server configuration.

This complete ZIP includes the base mappings needed for a fresh installation;
**no earlier ZIP is required**. It combines the preserved base files with the
updated main packs and mappings from the 1.0.3 overlay. The separate public 1.0.3
overlay assumes an existing base installation and is not the complete download
linked above.

## Included content

| Files in the complete ZIP | Installation and purpose |
| --- | --- |
| `packs/SlimefunBedrockRP_1.0.1.mcpack` | Required main pack for Slimefun Bedrock resources. |
| `packs/Albion_ValhallaMMO_Bedrock_1.0.1.mcpack` | Required main pack for the bundled Albion item and equipment mappings. |
| `custom_mappings/` | All 23 JSON files are required for the complete bundle: 20 Slimefun item mappings, one Albion item mapping and two skull mappings. |
| `optional/Albion_ValhallaMMO_Stat_Icons_1.0.0.mcpack` | Optional ValhallaMMO stat/effect text icons; not installed by default. |
| `INSTALL.md` and `README.txt` | Complete-install instructions and the unchanged upstream overlay notes. |

The mapping files contain **507 Albion item definitions** and **1,543 unique
custom skull hashes**: the original 1,453 plus 90 additional hashes. The two main
packs contain the geometry, armor and material changes supplied by the 1.0.3
overlay. Component versions remain 1.0.1, as shown in their filenames. All 27
supplied component files are copied unchanged; the complete outer archive adds
`INSTALL.md`. The earlier-base prerequisite in the preserved `README.txt` is
already satisfied by this complete ZIP.

These resources do not install ValhallaMMO or supply its server gameplay. The
optional stat-icon pack is separate from the two required main packs and can be
left out.

## Install or update the drop-in files

1. Install and configure [Geyser](https://geysermc.org/wiki/geyser/setup/) and
   confirm that a Bedrock player can connect to the Java server. Use a Geyser
   build supporting the item and skull mapping formats described below.
2. Stop the server or proxy running Geyser normally. Back up its data folder,
   including existing mappings and resource packs, before changing any files.
3. When upgrading, move the older versions of the two main packs outside the
   active `packs/` directory after backing them up. The updated packs retain the
   same UUIDs, so only one version of each should be active. Use the table below
   to identify the older files. Preserve unrelated packs, mappings and config.
4. Extract `SFL_GEYSER_RP_experimental_v1.0.3_complete.zip`. Copy the two `.mcpack`
   files from its root `packs/` directory into Geyser's `packs/` directory and
   all 23 JSON files from `custom_mappings/` into Geyser's matching directory.
   Merge the directories and replace the corresponding backed-up mapping files.
   Keep each `.mcpack` as a file; the outer ZIP itself is not a resource pack.
5. If wanted, copy `optional/Albion_ValhallaMMO_Stat_Icons_1.0.0.mcpack` into
   Geyser's `packs/` directory. This optional font pack is unchanged from the
   earlier bundle. Keep at most one installed copy; leaving it under `optional/`
   does not activate it.
6. Set `enable-custom-content: true` under the existing `gameplay:` section of
   Geyser's `config.yml`. Start Geyser normally and inspect its startup log for
   pack or mapping errors. A complete restart is required for the registrations.
7. Reconnect Bedrock players and have them accept the pack update. Check
   representative Slimefun items, custom skulls and Albion equipment in the guide,
   inventory and hand before wider use. Check text icons if the optional pack is
   installed.

| Earlier main pack to back up and remove from the active folder | Replacement in this ZIP | Shared pack UUID |
| --- | --- | --- |
| `SlimefunBedrockRP.mcpack` | `SlimefunBedrockRP_1.0.1.mcpack` | `f3e14cb9-aea6-58a4-bd52-1bc3c9b9084a` |
| `Albion_ValhallaMMO_Bedrock_1.0.0.mcpack` | `Albion_ValhallaMMO_Bedrock_1.0.1.mcpack` | `38dd6eec-1713-5df4-9e88-037b3279d6cc` |

If an installed pack was renamed, identify it by the UUID in its manifest before
replacing it. Do not remove another pack just because its filename looks similar.

| Content | Geyser-Spigot destination |
| --- | --- |
| The two required main `.mcpack` files | `plugins/Geyser-Spigot/packs/` |
| All 23 JSON files, including both skull mappings | `plugins/Geyser-Spigot/custom_mappings/` |
| The optional stat-icon `.mcpack`, if selected | `plugins/Geyser-Spigot/packs/` |

When Geyser runs on a proxy or as a standalone process, install the files in that
running instance's `packs` and `custom_mappings` directories. Copying them only to
a backend Java server does not configure a separate proxy's Geyser. Do not create
an extra nested `Geyser-Spigot/` directory. Geyser's
[resource-pack guide](https://geysermc.org/wiki/geyser/packs/) documents platform
paths and pack delivery; its [custom-content guide](https://geysermc.org/wiki/geyser/custom-content/)
documents the mapping folder and configuration setting.

## Item and skull mapping formats

`albion_valhallammo_mappings.json` uses numeric `format_version: 2` and an `items`
object containing arrays of definitions for Java item IDs. This is the structure
in Geyser's current [custom-item documentation](https://geysermc.org/wiki/geyser/custom-items/).

`migrated-custom-skulls.json` and `albion_slimefun_legacy_skulls.json` use numeric
`format_version: 1` with a `skulls` object and `skin_hash` entries. Keep both as
JSON in `custom_mappings/`; do not rename them to `custom-skulls.yml`. Geyser's
[custom-skull documentation](https://geysermc.org/wiki/geyser/custom-skulls/)
uses this JSON format and explains that the older YAML file is migrated
automatically. Geyser fetches uncached public skull textures and generates its
skull resources at startup. The item and skull files intentionally use different
format versions.

The main Albion pack's `ResourcePackManager 2.4.6` metadata identifies a generation
tool. It does not declare a required installed extension, and the ZIP supplies none.

## Verified loading and remaining checks

The exact complete ZIP passed two isolated loader checks on **Geyser Standalone
2.12.0 build 1268**, using Java 25.0.4.1. The default installation loaded the two
main packs; a separate run also loaded the explicitly enabled optional stat-icon
pack. Both registered **1,543 custom skulls and blocks**, generated a skull pack
with 1,543 texture files, and shut down normally. All 28 supplied files remained
unchanged. The observed skull/block count is 1,543; the preserved upstream
`README.txt` describes a different count without its supporting reports.

Both checks retained **107 texture-size deprecation warnings** from the Slimefun
mappings. Those mappings need future migration to attachables before Geyser
removes that support. The isolated checks had no connected Bedrock client or live
Java backend. Rendering, hand and armor visuals, live item interactions,
production connectivity and embedded Geyser-Spigot/Folia behavior remain untested.
The pack remains experimental; complete texture coverage and compatibility with
other packs are not established. Missing upstream artwork has not been replaced
with another item's texture.

## Optional installation and exact download

Servers without Bedrock players can omit the download. It is separate from the
Java resource pack, `SlimefunLegacyRP.zip`, and the addon JAR bundle. Java resource
pack delivery does not install the Bedrock resources or Geyser mappings.

The complete ZIP is stored with this source at
[`compatibility/bedrock/SFL_GEYSER_RP_experimental_v1.0.3_complete.zip`](../compatibility/bedrock/SFL_GEYSER_RP_experimental_v1.0.3_complete.zip).
The [component ledger and loader results](../compatibility/bedrock/complete-pack-provenance.json)
record the preserved source files and the two isolated checks. Its exact bytes are pinned in
[`compatibility/bedrock-resource-pack-release.json`](../compatibility/bedrock-resource-pack-release.json),
so release acquisition does not depend on an older public asset remaining
available at a replaceable download URL.

| Identity | Value |
| --- | --- |
| Filename | `SFL_GEYSER_RP_experimental_v1.0.3_complete.zip` |
| Files | 28: 23 mappings, two required packs, one optional pack and two instruction files |
| Size | 2,390,264 bytes |
| SHA-256 | `60fb9fcfe19e7e5644ff7202fd83bcd2b73b9f7685f3a57797d73877153c014c` |
