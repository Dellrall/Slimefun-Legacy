# Paired addon storage regression

This core-owned gate builds and tests the accepted Networks and InfinityExpansion2
sources against the exact Slimefun core produced by the same workflow run. It then
runs their reviewed published JARs with that core and the original paired storage
fixture in two independent JVMs on the minimum supported Purpur version and on
Purpur 26.3. The source build outputs and classpath receipts remain separate,
required evidence alongside the exact runtime artifacts.

The source pins in `fixture-lock.json` are **integration test inputs**. They do not
select addon versions for the distribution matrix, declare the external repair
work finished, or authorize a release. Changes to those pins require review of
the external owner's final source and the corresponding fixture contract.

| Input | Version | Fixed source or build |
| --- | --- | --- |
| Networks | 1.0.60 | `d41d362c8b71073dca41abc24f6ef6a5a8688fff` |
| InfinityExpansion2 | 2.0.15 | `168815bb99e5701d3680095a9eb9170d83a19740` |
| Purpur minimum | 1.21.11 | 2568 |
| Purpur modern | 26.3 | 2652 |

The lock records each published artifact's official versioned URL, byte count
and SHA-256. Networks is 1,681,029 bytes with digest
`e355ce958bd1e3d3c8ddd65d7f56dbd2b8d4c605ca6b0f1025a34e65c6a808b2`;
InfinityExpansion2 is 1,707,539 bytes with digest
`897bd4de70c9219217ecfb0f8cf68f0147b6c38758a239085db39718dd686eef`.
Both original Java fixture source hashes are unchanged by this final pair update.

## What the gate verifies

The two original Java fixture files are copied from the pinned Networks checkout
without changes, after their hashes are checked. They use the real IE2 storage
unit, a physical controller and two monitors. The seed phase performs 24
roundtrips, checks monitor deduplication and topology rebuilding, and stores 192
tagged items without an inventory viewer. A separate JVM reloads that topology
and withdraws exactly 192 tagged items, preserving the original fixture's
identity and conservation assertions.

The Gradle classpath receipt requires the same core JAR in each addon's compile
and test runtime classpaths. Networks uses its existing direct JAR override.
IE2 uses its existing coordinate override and a disposable local Maven directory
containing only that exact core. Normal addon build/test and Java 21 artifact
checks remain required.

The workflow stages the published JARs under `published/` after both source builds
pass. Packaging verifies their full size and hash against the lock and copies
them to `networks.jar` and `ie2.jar` for native execution. The independently built
JARs are preserved under `compiled/` and recorded in `compiled_inputs`, with their
own full artifact identities and the original compile/test core classpath
receipts. Every input validation checks both sets. The compiled artifacts can
differ from the published artifacts; the native runtime artifacts must match the
reviewed publication and the canonical bundle exactly.

Each native job creates a new world strictly inside `RUNNER_TEMP`. The small
`PairedStorageReceipt` companion observes loaded plugin metadata, native version,
a unique boot token, process identity, primary-thread execution and normal server
shutdown. It does not schedule work or read worlds, chunks or storage. Installed
input hashes must match before and after both JVMs. Full native logs provide
ordered startup, fixture completion and shutdown markers; unexpected errors in
either native logs or captured stdout fail the job. A timeout always fails.

Database snapshots run only after the child process has exited and its captured
output has closed. They preserve the database and any WAL/SHM/journal sidecars,
then inspect a separate read-only copy that includes WAL transactions. Original
and preserved-copy hashes must remain unchanged. Both post-exit ledgers are
required:

| Persisted state | Seed | Verify |
| --- | ---: | ---: |
| Physical block records | 4 | 4 |
| Block data rows | 4 | 4 |
| Inventory rows | 2 | 1 |
| Cached storage amount | 128 | 0 |
| Storage inventory slots | 13, 16 | 13 |
| Universal records/data/inventories | 0 | 0 |

The exact four record identities, monitor directions and storage settings must
remain present. Slot 13 is the display template and is excluded from the item
ledger. Seed slot 16 holds the physical 64-stack alongside the 128 cached items.
This post-exit check catches record loss during shutdown even when the live
fixture reported a successful operation.

The workflow uploads input provenance, both phase results, native/stdout logs,
receipt JSON and post-exit database evidence. It contains no publication step.
Coverage is limited to this fixed integration and orderly restart on these
Purpur builds. Client packet behavior, Folia ownership, abnormal termination and
other addon paths require their own evidence.

## Binding a final release to its runtime evidence

Changes to the canonical addon matrix also trigger this regression workflow.
Before publication, the release workflow separately requires the exact core and
packaged Networks/IE2 JAR bytes to match a successful native run, both paired
storage lane receipts, and the exact bundle used by a successful full-stack run.
An older test pair with the same version strings cannot satisfy this check.

The test-only source lock remains independent of distribution selection. This
update binds it to the external repair owner's accepted final pair and retains
the original fixture contract. Until the canonical inputs agree and their
runtime jobs pass, the final release guard rejects publication. A passing guard
does not grant publication authorization.

## Focused runner controls

These checks start no server and also run with Python optimization enabled:

`python3 -m unittest scripts/test_paired_addon_storage_probe.py -v`

`python3 -O -m unittest scripts/test_paired_addon_storage_probe.py -v`

They reject stale or incomplete receipts, wrong source/platform/artifact identity,
errors in either log stream, unsafe fixture directories, late success after a
deadline, and incorrect or lost post-exit database records and balances.

