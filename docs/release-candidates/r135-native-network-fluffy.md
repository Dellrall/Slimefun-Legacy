# r135 native Networks ↔ Fluffy Barrel integration probe

Only a **disposable CI Paper 26.3 full-stack world** is used. This test is not distributed
in Slimefun Legacy, Networks or FluffyMachines JARs, and cannot run on an arbitrary
production directory. It skips cleanly when the tested manifest revision is not r135.

The standard full-stack smoke first launches all 45 addons twice and verifies Slimefun's
clean-shutdown marker. The new staging-only probe then compiles a temporary Java test
plugin against the **exact installed binaries**. A third offline Paper process runs the
registered `SMALL_FLUFFY_BARREL` ticker and actual `NetworkRoot.getFluffyBarrel`
adapter without replacing either implementation.

The native case asserts:
- Exact **Slimefun 4.1.74, Networks 1.0.54, FluffyMachines 26.2.16**, with SHA-256
  pin provenance against the exact r135 source manifest.
- Real 17-diamond item deposit, physical output read, and Networks discovery including
  custom PDC and 64-bit data.
- Rejection of wrong-owner metadata and zero/negative withdrawal requests without
  changing stored quantities.
- Exact 12-item Networks extraction, a 9-item network-adapter deposit, and final
  14-item withdrawal: `12 + 14 = 17 + 9`.
- Complete drain, safe reassignment to a different custom-item type, rejection of
  the previous diamond template and a six-emerald recovery with metadata unchanged.
- Server shutdown, process exit code, full console logs, exact input JAR digest,
  test source compilation evidence and a machine-readable result.

This tests actual block-menu and storage-adapter behavior in a headless disposable
world, not asynchronous third-party inventory races, full controller topology,
external chunk unload, world upgrade, crash atomicity or AlbionMC's live TPS.
Keep those claims out of release notes until separately tested. Any failure blocks
the staging full-stack lane but never changes the published v4.1.73/r134 assets.
