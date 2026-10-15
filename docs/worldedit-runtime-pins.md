# Reviewed WorldEdit runtime dependencies

This is disposable CI setup only, not a Minecraft server updater. It changes no
Slimefun Java source, addon selections, release version, server configuration or
player/world data. It remains separate from backpack completion PR #387.

## Why explicit pins

After the successful #385 PR matrix, post-merge full-stack run `38735334998`
failed before startup while downloading WorldEdit. Retrying the failed jobs
without altering the source did not resolve it. A bounded read-only audit
`38739886940` reproduced HTTP 404 at the official WorldEdit 7.4.6 CDN URL both
with automatic selection and an explicit `YFnqiUlL` request on 26.2 and 26.3.

Audit artifact `11976425317` was downloaded and independently verified:
`bb660409d1bc68750a6b909380f4e9b979afed14b257d87f9852c84fff94c67a`.
This is transport evidence, not a Slimefun gameplay failure or permission to
omit WorldEditSlimefun from the required addon roster.

## Reviewed selection

| Runtime | WorldEdit | Official version ID | SHA-256 |
| --- | --- | --- | --- |
| 1.21.11 / Java 21 | 7.4.2 | p8T2aZ8U | 0ee152b1be5dfb51500505e2bf5a8c9d66f09c7fa484bf9aea384d7e7b459b06 |
| 26.2 / Java 25 | 7.4.5 | F5ea2ov3 | e5696a6d064b9969437a8888be91b0941148a28e0c3736de1554a00254a5d142 |
| 26.3 / Java 25 | 7.4.6-beta-02 | J1eeOh6C | 166365c44bad4cd916200b288cf391d3770e3197d1eca84ff74f3914d933e289 |

The 1.21.11 identity/digest comes from the actually successful master #385
runtime artifact `11973288512`, independently downloaded with artifact SHA-256
`70a9fb5542b74cf01187c4f18970d880b3a4dacb646ba5e21fcbf904f23d23e6`.
It recorded WorldEdit 7.4.2 after rejecting newer Java-25 builds.

The 26.2 and 26.3 alternatives were explicitly inspected using the original
metadata/hash/JAR/bytecode verifier in audit `38740425854`, artifact
`11974997212`, independently downloaded with SHA-256
`9077e669f0547dbfa13362633b96d3ec316e1b7365ba304e89c89c71e0311079`.
Both selected artifacts downloaded and passed those checks. The audit's overall
failure records that its bounded three-alternative 1.21.11 search encountered
only Java-25 builds; it does not invalidate the individually verified 26.x
artifacts. The earlier successful 1.21.11 runtime supplied its appropriate pin.

## Policy

The command-line helper now selects these reviewed IDs by default. It still
requires official source identity, explicit upstream Minecraft/loader support,
allowed release channel, published size/SHA-512, safe JAR structure, plugin
identity and applicable Java bytecode. The independent SHA-256 pin is checked
before publishing staged files and again during CLI staged/log verification.
WorldEdit and WorldEditSlimefun must still actually enable on every boot.

This is explicit version selection, not automatic fallback after a failed
transport/hash/identity check. A failed pin remains a failed check. The 26.3
beta still requires `--allow-prerelease`; selecting it does not grant that flag.
Do not describe this as stable-only dependency coverage on 26.3.

The existing explicit `--version-id` override is retained for reviewed replay.
Selecting the configured ID still requires its SHA-256. A different explicit
ID retains the existing strict upstream metadata/hash/JAR policy rather than
silently substituting another version. The library `stage()` API keeps its
existing unpinned behavior unless a caller supplies an expected digest; this
lets the separate audit inspect upstream drift without changing runtime pins.

## Tests and gate

Eleven new offline policy tests pass locally, including all three CLI modes,
identity/digest mismatch, pre-publication rejection, explicit overrides,
no retry/fallback on transport failure and no implicit prerelease permission.
They use mocks for network/validated-artifact results and do not certify real
WorldEdit runtime operation. Existing dependency tests remain unchanged.
The exact helper baseline blob was independently reconstructed and verified as
`faf79abda0440084b390f0905e8ee6d5c5d49c49`; candidate blob is
`f975108db76c432c13574f979471faedecffafc2`.

Require the real four-platform full-stack gate, including all 45 addons,
restart evidence and existing conservation/receipt probes before merging this
CI-only change. Then revalidate other active candidates on the integrated
source. No original failed run is retroactively called green.
