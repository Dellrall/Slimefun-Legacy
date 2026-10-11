## Addon bundle refresh — revision 131

The current **SF_Addons_1.21.11-26.3.zip** replaces Networks 1.0.50 with **Networks 1.0.51**. The other 44 addon JARs, published Slimefun Legacy 4.1.73 core and optional resource pack remain byte-for-byte unchanged. The source matrix also pins Networks to the merged 1.0.51 release commit for future bundles.

Networks fixes the Crafter Manager `SlimefunItemStack` to `CraftItemStack` cast failure at `CrafterManager.updateDisplay`. Older bundled Dough can wrap a Slimefun stack inside Paper's delegate field, hiding it from the core's direct subtype check. Networks now normalizes the finished display icon through its existing clean-item helper immediately before writing it into the manager menu. Recipes, storage, item IDs and crafting behavior are unchanged.

The standalone release passed its Legacy, United and Gugu compatibility jobs, including 129 tests on the Legacy target. A native Purpur 1.21.11 build 2568 regression exercises the real `updateDisplay` and inventory write: repeated Slimefun outputs, full metadata preservation outside display decoration, source-item isolation, click handlers, dirty tracking, missing menus and ordinary stone outputs. The original Networks 1.0.50 reproduces the reported cast exception; the fixed candidate passes. The released 1.0.51 JAR also passed this native CI regression before publication.

The distributed JAR targets Paper 1.21.11 with Java 21 bytecode. The separate canonical bundle workflow must pass its pinned-source Paper 26.3 compile check before this refresh is merged. The archive's existing validation files remain historical evidence for revision 130; the targeted refresh verifies the current manifest and checksums and proves that all other addon bytes are preserved. Exact source and artifact hashes are recorded in `compatibility/bundle-refresh-r131.json`.

Publication checks that 4.1.73 remains the latest release, verifies its core and resource-pack hashes, and refuses to overwrite a changed live ZIP. It replaces only the addon ZIP. The original core release tag remains pinned to its original source.

For an existing server, stop it, replace `SF_Networks1.0.50.jar` with `SF_Networks1.0.51.jar`, and start normally. Keep a single Networks JAR installed; do not use PlugMan or `/reload`. No machine rebuild or data migration is required by this fix. Validation does not cover every historical world, the reported 82-plugin installation as a whole, or Folia region behavior.
