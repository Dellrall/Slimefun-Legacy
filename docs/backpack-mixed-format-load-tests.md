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

## Fixture boundaries

The fixture invokes the real private `ProfileDataController#getBackpackInv` path via reflection, uses the production `RecordSet`, `StoredInventoryReader`, item codec and incomplete-load guards, and counts real write/deletion submissions at the controller boundary. The submission adapter completes immediately and deliberately does not run the production write worker or update database rows. Success of the post-recovery save check proves the hold is released, not durable write completion.

Old-format records are generated using the existing historical writer in MockBukkit. They are format-contract fixtures, not captures from an actual old Minecraft server. Database connection reopen is not a new Minecraft server process. These tests do not claim full-world upgrade, arbitrary addon, Folia scheduler, crash-atomicity or reverse-fork compatibility.

## Verification

Run the project's actual Gradle suite, not a stub harness:

```sh
./gradlew spotlessApply
./gradlew test --tests 'com.xzavier0722.mc.plugin.slimefun4.storage.controller.BackpackMixedFormatLoadTest' --no-daemon
./gradlew build --no-daemon
```

At creation, these assertions have been written but CI has not yet established that they pass. No newly reproduced production defect or bug fix is claimed. Keep this PR separate from the Doctor registration fix and inspect the exact-head JUnit XML before reporting a result.
