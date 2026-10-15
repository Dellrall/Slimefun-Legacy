# Backpack save completion ownership

## Scope

Follow-up to the merged mixed-format loading tests in #385, based on
`66b1f89189629e583a07d9733db94c458b1a45f0`. This changes only the future
returned by the private backpack save-chain method, plus a regression class
and this scope record. Item/research IDs, metadata, quantities, recipes,
serialized bytes, database schemas, slot ordering, recovery behavior,
public method descriptors, addon pins and release versions are unchanged.

## Reproduced defect

`ProfileDataController.chainBackpackSave` returned the same mutable
`CompletableFuture` stored in `backpackSaveChains`. An API caller could
complete, fail, cancel or obtrude that returned object before the real
writer finished. Its cleanup callback would remove the tracked chain,
allowing a later stage to proceed without the intended persistence barrier.
This is an API/lifecycle defect, not evidence of player cheating or an
observed live item-loss incident.

Return `next.copy()` instead. Callers retain a normal mutable observation,
but cannot complete the internal signal that serializes subsequent saves,
holds cache lifecycle work and is observed during shutdown. Actual database
success/failure still reaches an unmodified observation. The existing
`QueuedWriteTask.getCompletionFuture()` already uses this ownership pattern.
Cancelling one's observation does not cancel an accepted database write.

## Permanent regression coverage

`BackpackWriteCompletionTest` adds 11 executions using the actual save-chain,
tracked writer task and production SQLite adapter against a disposable disk
database. A separate JDBC observer reads the persisted rows. Before/after
hooks inject deterministic failures around real writes; they do not replace
successful SQL work or the snapshot/queue implementation.

The suite covers unchanged saves, an exact stack move, staged bytes versus
later live edits, all five caller-completion variants, pre-delete and
post-write acknowledgement failures, the existing full 54-slot recovery
retry, removal of a fixture-only stale high slot, another backpack's
isolation, a queued newer stage after a failed predecessor, and normal
shutdown followed by a fresh adapter/controller load. It checks item type,
amount, opaque metadata and backpack/owner identity. An observed write
failure remains visible to shutdown accounting even after a successful retry.

## Baseline evidence

Test-only head `bf8d8c8ea1ad73338de949e9c59658bd09c6496b` ran unchanged
production source. Core build `38736876831`, artifact `11974342563`, was
downloaded and its SHA-256 checked:

`2a90ffca788f6bd18b9497ce5b4eca382bc8ce85b74c18d76184c18dca568a8b`

Actual XML: 865 reported tests, 5 failures, 0 errors, 1 existing skip.
The new class ran all 11 cases; exactly the five external-completion cases
failed because the internal chain count became zero while its real SQLite
writer was held. The other six cases passed. No other suite failed.

An earlier standalone Java 21 control-flow probe independently had 0/5
baseline and 5/5 detached-observer expectations passing. That probe is
separate from the actual plugin/SQLite baseline above.

The inspected production baseline blob is
`687221f42b1de3afe615d51bc8db01d218aa46ed`; the new test source blob is
`28fd8fa7be129b221477afb7584d54bf87a8fd56`.

## Candidate gate and limits

Candidate exact-head full Gradle/JUnit, formatting, bytecode/API/addon and
relevant runtime checks must pass before merge. Record their actual outcomes
on #387; the failed baseline is not candidate validation. No local full
Gradle build is claimed: the working container has Java 21 but cannot fetch
the project's dependencies and Java 25 toolchain.

The test controls initial adapter wiring and executor creation. It is not a
live Minecraft scheduler or Folia ownership test. Closing and reopening a
controller/adapter is not a Minecraft process restart. These tests do not
establish power-loss atomicity, a transaction across player/world/database
saves, old-world upgrade coverage or cross-fork rollback safety. No production
data, release asset, server configuration or resource pack is modified.
