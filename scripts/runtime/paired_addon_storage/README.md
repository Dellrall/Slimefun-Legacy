# Paired addon storage regression

This core-owned gate builds the fixed Networks and InfinityExpansion2 test sources
against the exact Slimefun core produced by the same workflow run. It then runs the
original paired storage fixture in two independent JVMs on the minimum supported
Purpur version and on Purpur 26.3.

The source pins in `fixture-lock.json` are **integration test inputs**. They do not
select addon versions for the distribution matrix, declare the external repair
work finished, or authorize a release. Changes to those pins require review of
the external owner's final source and the corresponding fixture contract.

| Input | Fixed test revision |
| --- | --- |
| Networks | `4e954b87a03ac84fc5357c49c315d155e8435e78` |
| InfinityExpansion2 | `1ee9e3a5566886d14f2cc1a9a0ea0ce55b400a27` |
| Purpur minimum | 1.21.11 build 2568 |
| Purpur modern | 26.3 build 2652 |

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

The test-only source lock remains independent of distribution selection. When
the external repair owner supplies the final accepted pair, its source and
fixture contract must be reviewed before updating the lock and bundle pins.
Until those inputs agree and their runtime jobs pass, the final release guard
rejects publication. A passing guard does not grant publication authorization.

## Focused runner controls

These checks start no server and also run with Python optimization enabled:

`python3 -m unittest scripts/test_paired_addon_storage_probe.py -v`

`python3 -O -m unittest scripts/test_paired_addon_storage_probe.py -v`

They reject stale or incomplete receipts, wrong source/platform/artifact identity,
errors in either log stream, unsafe fixture directories, late success after a
deadline, and incorrect or lost post-exit database records and balances.

