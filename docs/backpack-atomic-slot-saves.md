# Atomic backpack changed-slot saves — issue #390

## Scope

Candidate based on master `b5db114abe5703a8fb80466724c74e1796feab5a`.
The confirmed published-4.1.74 defect is recorded in #390: a two-slot move
could commit its insertion and deletion separately. This candidate changes
that persistence boundary, not item serialization or gameplay transfer rules.

The controller retains eager caller-side item snapshots/serialization,
per-backpack save chains, caller-future isolation and the existing uncertain
baseline/full-54-slot retry. One tracked write task now submits an immutable
changed-slot batch. The SQL adapter uses one connection, an explicit
transaction and commit-before-acknowledgement. All changed inserts/updates
and deletions either commit together or remain unacknowledged.

SQLite retains its existing per-adapter writer monitor. MySQL/MariaDB requires
an independently checked InnoDB backpack inventory table; PostgreSQL and
SQLite use their native upsert form. No database schema, durability setting,
payload, owner/backpack UUID, item/research ID, public existing method,
recipe, machine rate, addon pin, release identity or platform target changes.
Existing external adapters retain binary linkage but the new batch method
explicitly refuses until implemented; there is no non-atomic fallback.

Failed or uncertain commits are not automatically retried or acknowledged.
Rollback errors retain suppressed evidence, never reset unresolved transactions
to auto-commit, and attempt connection abort/eviction. A subsequent normal save
uses the existing full snapshot retry, itself now transactional. This is not a
protocol for coordinating another inventory, player file, server or writer.

## Regression coverage

- Seven separate-JVM controller/real-SQLite slot-move cases: normal shutdown,
  before a statement, after insertion, after deletion in the reverse-direction
  move, before commit, after real commit/before acknowledgement, and after ack.
  Each requires three distinct processes, nonce-bound markers, bounded waits,
  46 items after recovery, correct slots, original metadata, exact untouched SQL
  types/bytes, and isolation of another backpack. No restart read/no-op save may
  rewrite rows. Process termination exists only in the disposable test entry point.
- Real JDBC unit cases for either statement failure, rollback, lost commit
  acknowledgement, unresolved rollback, unknown database/caller-owned-transaction
  refusal, immutable staged bytes, supported external-database commit/rollback,
  and unsupported custom adapter refusal.
- Existing real-writer tests now intercept actual prepared statements. Failed
  statement expectations are strengthened from partial persistence to rollback;
  the lost-ack test interrupts after actual COMMIT, not after an individual write.
- Existing recording-only load/serialization fixtures intercept the new batch
  submission and retain their earlier row/staging assertions. These fixtures do
  not claim transaction durability. The existing one-slot process test's
  after-write boundary is now explicitly after the full transaction returns.

## Validation boundary

At creation this candidate is **not yet verified or released**. Local API
signature/annotation and inventory-persistence static checks pass; a full
Gradle build is not claimed locally because only Java 21 is installed and
external dependency hosts are not resolvable. Require exact-source Java 25
build/tests, pristine changed-file formatting, real disposable MySQL/PostgreSQL,
public API, migration, addon bundle and supported-runtime checks before merge.

These are synthetic items and controlled process exits, not historical-world,
Minecraft-client, OS crash, hardware power-loss, trigger-customization or
cross-inventory atomicity guarantees. Folia 26.3 expansion remains deferred.
Published core/addon assets and live Albion data remain unchanged.
