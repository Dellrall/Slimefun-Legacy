# Compatibility-first modernization: storage audit

## Scope and release contract

Minecraft 1.21.11 is the minimum supported server version. Paper and Purpur are the primary validation targets. Leaf and Folia remain supported targets, with separate owner-region, entity-scheduler and cross-region checks for Folia. Compilation or a startup-only smoke test is not proof of gameplay or persistence correctness.

Modernization must preserve existing item and research IDs, persistent keys, machine identities, backpack identities, inventory contents, saved block data, addon APIs and established gameplay behavior. Remove obsolete pre-1.21.11 runtime branches only when they are not also needed to read historical data or link an existing addon. Age of saved data is not the same as the server-version support floor.

Keep data-sensitive compatibility bridges until their replacements have behavioral and persistence evidence. An isolated, documented deprecated API call is preferable to silently changing a storage format. Do not introduce blanket warning suppressions or delete compatibility signatures to make compiler reports green.

GuGu is the sole active upstream maintenance and future interchange target. Historical data readers, addon contracts and prior fork-validation evidence remain intact; United is no longer an ongoing validation goal. Pin the exact GuGu and Legacy commits, Minecraft version and addons before claiming interoperability. Test switching Slimefun implementations on the same Minecraft version separately from changing Minecraft versions. Do not infer Minecraft downgrade safety from successful plugin rollback. See [ADR 0003](adr/0003-gugu-only-upstream-maintenance.md).

## Baseline inspected

Initial source checkpoint: `068de2d0056e2f5ce199c6c179a980f1e666622c`.

This is a scoped first audit, not a completed review of every storage path or addon. The following observations come from source inspection; they are not claims of successful old-world runtime testing.

| Boundary | Source observation | Decision / remaining evidence |
| --- | --- | --- |
| `me.mrCookieSlime.Slimefun.api.BlockStorage` | Historical static methods delegate to `BlockDataController`. Some reads load data. `getLocationInfo(location)` returns a live `BlockDataConfigWrapper` for existing data. | Keep the class and descriptors. Audit load/ownership, create/remove ordering and overloaded methods before changing delegation. |
| `BlockDataConfigWrapper` | Bridges old `Config` calls to the real data container. String values stay strings; file lifecycle methods are no-ops. `setValue(path, null)` removes data and then incorrectly throws. | Fix only the null fall-through and add focused contract tests in this batch. |
| `ASlimefunDataContainer` | Mutations update the cache and schedule persistence through `scheduleUpdateData`; pending-removal state changes the scheduling path. | Exercise delegation in memory now. Durable writes, cancellation, restart and concurrent lifecycle transitions need separate tests. |
| Legacy `Config` | The old public type is explicitly retained for addon linkage; wrappers use its protected constructor. | Keep the API. Do not turn the storage wrapper into a separate YAML writer. |
| `ItemStackDataCodec` | New records already use an `SF2` marker plus Paper-native item bytes; reads also accept historical Base64/Bukkit object streams. | Existing read compatibility does **not** establish that another fork reads Legacy-written records. Leave this codec unchanged while auditing exact readers, writers and migrations. |
| `build.gradle.kts` | Production API selection and the MockBukkit test API are deliberately separate; build toolchain is Java 25 and emitted bytecode is Java 21. | Preserve that separation. Unit-test success is not the 1.21.11 / 26.2 / 26.3 real-server matrix. |

### Questions deliberately left open

The legacy `BlockStorage` overloads have behavior that must be compared with real addon call sites before modernization: ID handling, `destroy` / `updateTicker` flags, missing-item retrieval, chunk access and lazy data loading. The wrapper's string-only default handling and flat-key behavior likewise must not be casually expanded into new coercion or path semantics.

The existing `SF2` writer is a concrete rollback review point. Inspect `DataUtils`, `DatabasePatchV3` and the readers in the exact alternative fork builds. Establish which existing rows are rewritten, when that happens, whether prior records remain recoverable and whether the alternative reader accepts the resulting bytes. Do not describe a forward migration test as a reverse-compatibility test.

## Batch 1: legacy null-deletion contract

### Defect

`BlockDataConfigWrapper#setValue(path, null)` calls `removeData(path)` and then falls through to `value instanceof String`. Because null is not a String, it throws `NotImplementedException` after the mutation has already happened. Callers can observe a failure even though a deletion was applied or scheduled.

### Change

Return immediately after `removeData(path)` for a null value. Continue rejecting non-null, non-string values with the existing exception. Do not stringify values, rename keys, bypass the data container, change save scheduling or modify any serialized format.

The production change does not alter a public method descriptor, item registration, resource-pack metadata, controller, schema, version target or addon source.

### Regression coverage

`src/test/java/com/xzavier0722/mc/plugin/slimefun4/storage/controller/BlockDataConfigWrapperTest.java` adds 15 JUnit tests using a recording subclass of the real `ASlimefunDataContainer` and calls through the historical `Config` type:

- Null deletion for present, absent, repeated, unloaded and pending-removal cases; neighboring values and container identities remain unchanged.
- Exact opaque string and empty-string handling; rejected non-string writes and defaults do not mutate data.
- Existing defaults, new defaults, detached key enumeration and read-only lookups.
- No-op file lifecycle methods and isolation between separate wrappers.

The recording subclass captures update requests; it does not write a database or impersonate a real Folia scheduler. These tests therefore protect the bridge contract, not durable storage, crash recovery or cross-region safety.

### Validation evidence and limitations

An isolated Java 21 harness ran the same 15 test bodies: the unmodified wrapper passed 9 and failed 6; the fixed wrapper passed all 15. The original wrapper and two data-container source copies were checked against their Git blob hashes. For this local-only harness, external dependencies were stubbed and the two Lombok getters were expanded. This is **not** a full Gradle/JUnit/MockBukkit result.

The local environment could not resolve GitHub for cloning and had no project dependency cache or Java 25 toolchain. GitHub CI must still run the real suite, formatting, production compilation, bytecode/API guards and relevant server checks. Nothing in this audit marks those checks, cross-fork rollback or an old-world upgrade as passed.

Focused CI reproduction command:

```sh
./gradlew test --tests 'com.xzavier0722.mc.plugin.slimefun4.storage.controller.BlockDataConfigWrapperTest' --no-daemon
```

Also require the existing full build and invariant gates; the focused command is not a substitute.

## Batch 2: concurrent pending-removal cancellation

### Defect and addon relevance

At core `6feeddf224e2a987b306a8b69a6ec13d6e071293`, `setData` and `removeData`
could observe pending removal before the capture helper observed its cancellation.
The mutation then changed the cache without either retaining the change for replay
or submitting it for persistence. Cancellation could also replay an older captured
value or deletion over a newer active mutation.

This lifecycle occurs in `BlockListener`: it marks block data pending before an
item's break handler and cancels removal if that handler cancels the break. The
addon-facing data API is also used for stored amounts. For example,
[`NetworkQuantumStorage.syncBlock` at Networks PR #104's inspected source](https://github.com/wickidcow/SF_NetworksExp/blob/01ad4384de3d53234c04a49f148e400886d249f3/src/main/java/io/github/sefiraat/networks/slimefun/network/NetworkQuantumStorage.java)
submits the quantum-storage amount through `SlimefunBlockData.setData`. The same
class reads that field when reconstructing its cache. This establishes a relevant storage
boundary; it does not attribute a reported live duplication incident to this race.

### Change and compatibility boundary

A monitor for each container orders cache mutations, the pending-state decision,
captured changes and cancellation replay. Synchronizing on the container itself
also shares the reentrant monitor used by a synchronized addon override; a second
private monitor would introduce an avoidable lock-order inversion during virtual
replay. Captured changes still
coalesce by key, and a retained deletion still clears data supplied by a load
before submitting that deletion. Permanently removed containers do not replay.

Reads and the lower-level cache primitives remain lock-free. The controller can
read cached values while holding its delayed-write queue lock, so taking the
mutation monitor from those reads would introduce a lock-order inversion.
The weak capture registry is used only for short lookup/removal operations; it is
not held while persistence submissions run.

The public and protected method descriptors, keys, opaque string values, empty
strings, identities and persisted formats remain unchanged. The ordering contract
is for mutations on the same container instance. The existing copy constructor
shares a cache with another container; this change does not establish an atomic
move across those instances or a transaction across several data keys.

### Regression scope

Controlled worker interleavings exercise a write and a deletion at the capture
boundary, and older replay values/deletions racing newer active mutations. The
tests use the real production container with a thread-safe recording persistence
callback, bounded latches and worker-failure propagation. They compare the final
cache with the submitted values and separately check that an unrelated container
can make progress and a synchronized addon override remains usable.

The unmodified production class ran the first 19 JUnit cases: the 14 existing
cases passed and all five new race cases failed with the expected value/deletion
divergences. After the fix and three additional compatibility checks, all 22
`PendingRemovalReplayTest` cases and all 15 `BlockDataConfigWrapperTest` cases
passed locally, with no failures, errors or skips. The focused command is:

```sh
./gradlew test \
  --tests 'com.xzavier0722.mc.plugin.slimefun4.storage.controller.PendingRemovalReplayTest' \
  --tests 'com.xzavier0722.mc.plugin.slimefun4.storage.controller.BlockDataConfigWrapperTest' \
  --no-daemon
```

These are persistence-submission and lifecycle regressions. Database durability,
abnormal termination, complete addon item conservation and Folia region ownership
remain separate runtime evidence. The unreleased 4.1.76 candidate and the final
Networks/IE2 pair remain subject to the publication hold and exact-source gates.

## Remaining execution order

1. Stabilize the core API and compatibility layer, beginning with the scoped bridge fix above.
2. Audit BlockStorage, block/menu lifecycle, serialization and all data-sensitive paths before changing them.
3. Finish safe deprecated/removal-API modernization without widening compatibility suppressions.
4. Add permanent regression fixtures for items, machine data, inventories and world identities.
5. Verify current JEG and Networks fixes and extend reliability/performance coverage; do not restart completed work.
6. Modernize the canonical addon bundle in coherent, dependency-aware batches; pin every source revision.
7. Run old-world-to-candidate upgrade and clean-restart tests on disposable copies; compare identities, contents and machine behavior.
8. Run the 1.21.11 floor, maintained intermediate versions (including 26.2) and 26.3 matrix, prioritizing Paper and Purpur and separately validating Leaf/Folia.
9. Fix exposed regressions and repeat the affected tests. Validate reverse compatibility against exact alternative builds before making rollback claims.
10. Release only the tested core commit and its exact known-good addon bundle, with source revisions, artifact hashes and explicit test evidence.

Each batch must state the inspected source, changed behavior, unchanged persistence boundaries, tests actually run and outstanding validation. Do not publish or merge a speculative persistence migration merely because compilation succeeds.
