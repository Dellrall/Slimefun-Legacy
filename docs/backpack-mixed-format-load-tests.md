# Mixed-format backpack load preservation

## Scope

This is a test-only continuation of the core storage audit from master `c72fc1699934846bf25277c37640023b55aeb022`. It adds `BackpackMixedFormatLoadTest`; no production source, codec, database schema, identifiers, recipes, item counts, save policy, addon pins, release version or resource-pack files change.

Existing codec tests cover historical representations independently, and the original `InventoryReadFailureTest` exercises controller failures primarily using native binary item rows. The new suite checks the complete normal backpack inventory reader with mixed representations returned by a real disposable SQLite database.

## Added assertions

Two parameterized scenarios run for six encodings (12 executions): native SF2 binary, Base64-wrapped SF2 as binary or text, historical Base64 Bukkit object streams as binary or text, and historical MIME-wrapped text.

- Mixed rows retain material, quantity, opaque old-addon IDs, the stored backpack identity, owner metadata and exact stored text/binary representation. SQL `typeof` and `hex` snapshots ensure a successful read does not normalize or rewrite rows.
- Missing slots and historical null, whitespace-text and empty-binary slots remain empty.
- A malformed last row prevents a partial inventory from being returned, holds that backpack against subsequent save attempts, and submits no writes or deletes. Earlier readable rows remain unchanged.
- A second backpack remains readable; loading it does not release the first backpack's failure hold.
- Closing and reopening the SQLite connection retains the original mixed rows and the failure. An explicit fixture-only replacement of the damaged row permits a complete retry; the normal reader never makes that replacement itself.
- Constructing a backpack from the fully recovered contents establishes an unchanged snapshot. Saving it completes successfully without rewriting historical rows or submitting deletes.
- An explicit in-memory move from slot 8 to slot 1 submits exactly one item write and one targeted deletion. The test checks the backpack UUID, both slot keys, the serialized item quantity and metadata, and the unchanged other stacks.
- A repeated save after the intercepted completion submits nothing further. Reading the other backpack also adds no writes; the disposable database remains unchanged because the submission adapter does not execute its records.

## Recovered-save fixture correction

The earlier head `3b1652450a90de589705199714686b9fc915b04b` required a write immediately after constructing the recovered backpack. That expectation conflicts with the real constructor, which snapshots the supplied contents, and with `persistBackpackStage`, which deliberately returns a completed no-op for an unchanged inventory.

All six recovery cases failed that assertion in the prior core CI report. The corrected fixture first proves the unchanged no-op, then deliberately moves a stack before requiring exact write/deletion submissions. It does not remove the positive-write requirement or change the production save policy. The failure is a test setup defect, not evidence of a newly discovered live backpack data-loss bug.

## Fixture boundaries

The fixture invokes the real private `ProfileDataController#getBackpackInv` path via reflection, uses the production `RecordSet`, `StoredInventoryReader`, item codec and incomplete-load guards, and captures write/deletion submissions at the controller boundary. The submission adapter completes immediately and deliberately does not run the production write worker or update database rows. Success of the post-recovery save checks proves the hold is released and the intended records are staged, not durable write completion.

Old-format records are generated using the existing historical writer in MockBukkit. They are format-contract fixtures, not captures from an actual old Minecraft server. Database connection reopen is not a new Minecraft server process. These tests do not claim full-world upgrade, arbitrary addon, Folia scheduler, crash-atomicity or reverse-fork compatibility.

## Verification

Run the project's actual Gradle suite, not a stub harness:

```sh
./gradlew spotlessApply
./gradlew test --tests 'com.xzavier0722.mc.plugin.slimefun4.storage.controller.BackpackMixedFormatLoadTest' --no-daemon
./gradlew build --no-daemon
```

The October 15 correction requires fresh exact-head JUnit and current-base compatibility evidence. Earlier successful heads do not certify these changed assertions. See PR #385 for the dated CI results and checked artifact hashes; do not interpret this document as a passing-build claim. Keep this test-only change separate from production fixes and release publication.
