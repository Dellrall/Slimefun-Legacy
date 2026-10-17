# Folia 26.3 experimental readiness

**Status: experimental core-readiness passed. Not production certification.**

Initial readiness evidence tested official **Folia 26.3 build 3 (ALPHA)**,
server commit `597e413`, API `26.3.build.3-alpha`, on Java 25. The disposable
server booted twice with Slimefun Legacy 4.1.75. `/sf doctor upgrade` ran on both
boots without a BLOCKED result, storage reported ready with zero pending writes, and
the second boot observed the prior Slimefun shutdown as clean. Current readiness
runs additionally enforce the repository's Folia Phase 1 scheduler/network and Part 4
event-safety invariants before the runtime boot.

Slimefun Legacy keeps Paper as its primary platform. This milestone adds a dedicated
Folia **26.3** core smoke test after Folia builds became available for the 26.3 line.
It does not promote Folia to the same support level as Paper or Purpur.

## What the lane verifies

The dedicated workflow:

1. Resolves the official Paper 26.3 API and builds the normal universal Slimefun Legacy JAR.
2. Downloads an official Folia 26.3 server build from PaperMC's Folia build service.
3. Starts a disposable Folia server twice on Java 25.
4. Requires Slimefun to enable with the exact candidate version.
5. Runs `/sf doctor upgrade` on both boots and refuses a BLOCKED result.
6. Requires a normal shutdown and verifies that the second boot observes the previous
   Slimefun shutdown as clean.
7. Preserves the exact tested Folia build/channel, logs and smoke result as Actions evidence.

The existing Folia 26.2 smoke remains unchanged.

## What it does not certify

A green readiness lane does **not** establish:

- safety of every Slimefun addon on Folia;
- cross-region Cargo or energy-network transactions;
- arbitrary machine layouts spanning Folia region ownership;
- live-player menus, combat or every entity callback;
- existing production worlds or downgrade safety;
- crash/power-loss durability beyond the separately tested storage boundaries.

Slimefun's existing Folia Phase 1 boundary remains: location/entity work must execute
through the owning scheduler, and Cargo/energy behavior must not silently become a
cross-region transaction merely because startup succeeds.

Every installed addon must independently be Folia-safe. Server owners should use a
cloned world and complete plugin set before considering any production migration.

## Promotion rule

Folia 26.3 remains **experimental** until representative region-owned gameplay,
machine/network behavior and maintained-addon compatibility have their own evidence.
Core two-boot readiness alone is necessary but not sufficient for promotion.
