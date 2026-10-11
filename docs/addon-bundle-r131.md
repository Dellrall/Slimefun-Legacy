## Addon bundle refresh — revision 131

The current **SF_Addons_1.21.11-26.3.zip** replaces Networks 1.0.50 with **Networks 1.0.52**. The other 44 addon JARs, published Slimefun Legacy 4.1.73 core and optional resource pack remain byte-for-byte unchanged. The source matrix also pins Networks to the merged 1.0.52 release commit for future bundles.

Networks 1.0.52 includes the Crafter Manager fix and repairs the same `SlimefunItemStack` to `CraftItemStack` cast failure in Quantum Manager, Drawer Manager, both Item Flow Viewer screens and Linker Grid rendering. Older bundled Dough can hide a Slimefun stack inside Paper's delegate field. Networks now normalizes each affected finished icon with its existing clean-item helper before writing it to the menu. Recipes, storage, item IDs, counts, transfer operations and crafting behavior are unchanged.

The standalone release passed Legacy, United and Gugu compatibility, including 129 tests on the Legacy target, and all nine native Purpur 1.21.11 build 2568 cases. These cover the three managers, both flow screens, Linker Grid rendering, drawer and Quantum previews, and the optional Quantum world item display. Checks exercise real inventory writes and preserve metadata, source samples and stored counts as applicable. The five additional failing writes were reproduced before patching. Linker testing covers its display with the optional provider absent, not live LogiTech transfers.

The distributed JAR targets Paper 1.21.11 with Java 21 bytecode. The separate canonical bundle workflow must pass its pinned-source Paper 26.3 compile check before this refresh is merged. The archive's existing validation files remain historical evidence for revision 130; the targeted refresh verifies the current manifest and checksums and proves that all other addon bytes are preserved. Exact source and artifact hashes are recorded in `compatibility/bundle-refresh-r131.json`.

Publication checks that 4.1.73 remains the latest release, verifies its core and resource-pack hashes, and refuses to overwrite a changed live ZIP. It replaces only the addon ZIP. The original core release tag remains pinned to its original source.

For an existing server, stop it, replace the previous Networks JAR with `SF_Networks1.0.52.jar`, and start normally. Keep a single Networks JAR installed; do not use PlugMan or `/reload`. No machine rebuild or data migration is required by these display fixes. Validation does not cover every historical world, the reported 82-plugin installation as a whole, or Folia region behavior.
