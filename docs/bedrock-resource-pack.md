# Optional Bedrock resource pack — Geyser required

Slimefun Legacy provides **`GEYSER_SFL_RP_Experimental_v0.0.1.zip`** as an optional
download for servers with Bedrock players. It contains a Bedrock resource pack and
the matching Geyser custom-item mappings. **Geyser must already be installed and
configured, and both the pack and the mapping files must be installed for this
integration to work.** The archive contains no Geyser plugin JAR or server config.

The held 4.1.76 candidate carries forward the exact ZIP already available on
[v4.1.75](https://github.com/wickidcow/Slimefun-Legacy/releases/download/v4.1.75/GEYSER_SFL_RP_Experimental_v0.0.1.zip).
It remains an **experimental 0.0.1** resource pack. Its inclusion does not establish
complete texture coverage, compatibility with every other pack, or successful
rendering on every supported Bedrock client. Core and addon publication remains
subject to the existing release hold.

## Install the drop-in files

1. Install and configure [Geyser](https://geysermc.org/wiki/geyser/setup/) first,
   and confirm that a Bedrock player can connect to the Java server.
2. Stop the server normally and back up the existing Geyser data folder.
3. Extract the outer `GEYSER_SFL_RP_Experimental_v0.0.1.zip`. Copy **both** sets of
   files below into the existing Geyser-Spigot installation, merging directories
   while preserving unrelated packs, mappings and configuration.

| Files inside the downloaded ZIP | Destination for Geyser-Spigot |
| --- | --- |
| `Geyser-Spigot/packs/SlimefunBedrockRP.mcpack` | `plugins/Geyser-Spigot/packs/SlimefunBedrockRP.mcpack` |
| All 20 JSON files in `Geyser-Spigot/custom_mappings/` | `plugins/Geyser-Spigot/custom_mappings/` |

4. Keep the `.mcpack` as a file. The outer ZIP is an installation bundle; place
   its contents in the locations above rather than placing that ZIP in `packs`.
   Avoid adding a second `Geyser-Spigot` directory inside the existing one. If
   these named Slimefun files are already installed, back them up before replacing
   them; retain unrelated files.
5. Ensure Geyser's `enable-custom-content` setting is enabled. In the current
   configuration format it is under `gameplay`. Start the server normally and
   check Geyser's startup log for pack or mapping errors.
6. Have Bedrock players reconnect and accept the offered resource pack. Check
   representative Slimefun items in the guide and in hand before wider use.

For Geyser installed on a proxy or as a standalone process, use the `packs` and
`custom_mappings` directories belonging to that running Geyser installation. The
`Geyser-Spigot/` directory in this download supplies the layout; it does not change
where Geyser runs.

Geyser's official [resource-pack instructions](https://geysermc.org/wiki/geyser/packs/)
and [custom-item instructions](https://geysermc.org/wiki/geyser/custom-items/#loading-mappings-and-resource-packs)
describe pack delivery, custom-content enablement and these directories.

## Optional installation and exact download

Servers without Bedrock players can omit this download. It is separate from the
Java resource pack, `SlimefunLegacyRP.zip`, and from the addon JAR bundle. Java
resource-pack delivery does not install the Bedrock pack or Geyser mappings.

The release process preserves the reviewed archive without changing its textures,
mapping identifiers or nested pack bytes. Its source asset and checksum are pinned
in [`compatibility/bedrock-resource-pack-release.json`](../compatibility/bedrock-resource-pack-release.json).

| Identity | Value |
| --- | --- |
| Filename | `GEYSER_SFL_RP_Experimental_v0.0.1.zip` |
| Size | 226,576 bytes |
| SHA-256 | `ba4fa277fb71a33ca557e0206ea51c40680593952a5d47fbd849b335c9fe09bf` |

