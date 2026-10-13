## Addon bundle refresh — revision 133

This targeted refresh of **SF_Addons_1.21.11-26.3.zip** for the published **Slimefun Legacy 4.1.73** core advances two independently validated addons already selected in the maintained-source matrix. It starts from the published revision-131 ZIP and applies the queued revision-132 FNAmplifications update, followed by the requested Supreme update. All other **43 addon JARs** are retained byte-for-byte, with no changes to the Slimefun core JAR or optional resource pack.

| Addon | Bundled earlier | Included in revision 133 | Pinned source commit |
| --- | --- | --- | --- |
| FNAmplifications | 4.2.7 | 4.2.8 | `24856fcb4efabb4edf900bf5d3e6a23cb9ba827f` |
| Supreme | 1.0.20 (older build) | 1.0.20 (updated JAR, same filename) | `17693b1eec0ef15f198c86a5803f6e5dbd085074` |

**Supreme 1.0.20** retains its existing numeric version and filename but advances to the October 13 tested source. The JAR includes true Slimefun Soulbound byte flags and safe legacy-ID recognition, restores all 11 Thornium armor potion effects (including Resistance, Strength, and Haste), repairs the historical `fall_damage` alias to Feather Falling, and adds the read-only `/supreme doctor soulbound` and `/supreme doctor armor` commands.

**FNAmplifications 4.2.8** prevents drags into the Gem Unbinder's temporary selection inventory without changing normal player-inventory drags or its recipe/reward settings. This is the source selection already described in the revision-132 candidate notes.

### Sources and checks

- Supreme [source merge](https://github.com/wickidcow/SF_Supreme/commit/17693b1eec0ef15f198c86a5803f6e5dbd085074) and [six successful CI jobs](https://github.com/wickidcow/SF_Supreme/actions/runs/38471806717). Release JAR SHA-256: `e03299368a57ace781737fc34bf3835c9590abf4c59a107544e66b2fbfbeb735`.
- FNAmplifications [source](https://github.com/wickidcow/SF_FNAmplifications/commit/24856fcb4efabb4edf900bf5d3e6a23cb9ba827f) and [green release checks](https://github.com/wickidcow/SF_FNAmplifications/actions/runs/38152097441). Release JAR SHA-256: `06ecc5824c9a295e44c282370e0d11c3c388013c2ff25c8bc34cf43c43a7b21f`.
- Previous published ZIP revision-131 SHA-256: `34b7c151c013d18a0d9da872b54fd0ca6a4502eeeb74ed1989d8e935a75b9d4b`.
- Targeted refresh requires exact source pins, bytecode <= Java 21, unchanged JARs and non-addon ZIP members, and a validated manifest with all 45 addon checksum entries. Publication also checks the current release's old ZIP/core/resource-pack SHA-256, and refuses to replace an unexpectedly updated release.

This does **not** bump the Slimefun core version or change the supported Minecraft 1.21.11 through 26.3 range. It is not a live-world test; administrators should back up the server, replace the old Supreme JAR rather than installing a duplicate, restart normally, and test armor effects/Soulbound using the diagnostic commands.
