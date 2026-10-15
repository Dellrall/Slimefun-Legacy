# Backpack process-boundary regression coverage

## Scope

This test-only follow-up starts from master
`f55c886c9e46625dd05848cd2976f3f20efdcaf5`, after mixed-format loading
#385, real-writer completion isolation #387, and CI prerequisite #388.
No production source, saved format, item/research identity, recipe,
quantity rule, machine rate, addon pin, dependency, workflow, platform
selection, release version or published asset changes.

`BackpackProcessRestartTest` launches `BackpackProcessProbe` in separate
JVMs for seeding, writing and verification. Each of four cases requires
three distinct process IDs, exact expected exit codes and a per-test
nonce in success markers. Child processes have bounded timeouts and
are forcibly terminated and reaped on timeout. Classpath discovery
includes Gradle's test classloader URLs rather than relying only on the
worker's `java.class.path`.

## Boundaries under test

| Boundary | Required fresh-process result |
| --- | --- |
| Acknowledged save, normal controller/adapter shutdown | Edited slot loads with its new quantity and original metadata |
| Deliberate JVM halt before the adapter performs the write | All originally committed inventory rows remain byte/type-identical |
| Deliberate JVM halt after the adapter writes, before its caller receives acknowledgement | The single committed slot update loads without rewriting unrelated rows |
| Deliberate JVM halt after the save future acknowledges completion | The acknowledged slot update survives without clean-shutdown assistance |

The edited slot deliberately changes from 23 to 7 items. The test does
not represent that administrative fixture edit as a gameplay transfer
or claim unchanged aggregate quantity. Both backpacks retain their
UUIDs, owner UUID, inventory sizes, names and backpack numbers. Their
items retain the existing addon ID, opaque long PDC value and complete
item metadata. All other inventory rows must retain their exact SQLite
storage types and bytes. Fresh-process reads and unchanged saves must
submit no writes/deletions and leave the database rows unchanged.

The writer uses `ProfileDataController`, its tracked production writer
queue and the real `SqliteAdapter` against a temporary disk database.
The fixture only controls adapter/executor wiring, seeding, and the two
latch boundaries around the real adapter write. It never opens Albion
or other operator files. Runtime.halt exists only in the test child
entry point, not production code or the JUnit worker.

## Evidence and limitations

At creation, these new tests are **unverified** pending exact-head CI.
The pre-change post-merge report was independently downloaded from
core run `38747154081`, artifact `11980166743`, and SHA-256 checked:
`abfbc040ba6e8efb442814b14b4394b94e9c07a2e3cba535b4438df9a7c5fd29`.
It contains 154 suites, 865 reported tests, zero failures/errors and one
existing real-database migration skip, including all 11 real-writer and
12 mixed-format executions. Those results do not certify this new test.

A process boundary is stronger evidence than reopening an adapter in
the same JVM, but this remains a MockBukkit-backed fixture, not a real
Minecraft server/client session or an upgrade of an historical world.
Only a single inventory-row edit is interrupted. Multi-slot, cross-player,
world/database atomicity, arbitrary kill points, device power loss,
OS crashes, failed fsync, MySQL/PostgreSQL and broad Folia safety are
not established. No automatic recovery, ledger repair or item rewrite
is introduced. Folia 26.3 is explicitly deferred by the owner and no
Folia lane is changed.

Java's Runtime.halt terminates without the normal shutdown sequence:
https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html
SQLite distinguishes application-process interruption from OS/power-loss
durability, especially across synchronous/journal configurations:
https://www.sqlite.org/pragma.html#pragma_synchronous

Run the repository's real formatting/build/test and supported-platform
gates before merge. No local full Gradle build is claimed: the working
container has Java 21 and cannot resolve GitHub. Keep existing released
core, addon ZIP and resource pack unchanged during this work.
