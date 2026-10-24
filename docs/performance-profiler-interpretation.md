# Reading `/sf tick top`

The Slimefun profiler reports **accumulated timing for Slimefun ticker
callbacks** in one requested sample. It does not measure the whole server,
including vanilla entities, world generation, networking, other plugins, or
the complete main-thread duration.

The output labels intentionally distinguish:

- **Total sampled ticker work** — sum of sampled Slimefun and addon ticker
  callback durations, aggregated over the sample; this is **not** server MSPT.
- **Ticker interval** — number of Minecraft ticks between Slimefun ticker
  cycles, with a *theoretical* seconds conversion at 20 TPS; this is **not**
  a measurement of how long the sample took on a live server.
- **Performance rating** — the project's historical Slimefun-specific
  profiler grade, currently comparing aggregate work with a 100 ms reference
  budget; this does not measure overall TPS.

An example production sample recorded **51.37 ms** of Slimefun callback work
across **1,818** blocks with a configured ticker interval of **10 ticks**.
Of that, **32.31 ms** was aggregated across **400** upstream Networks
autocrafters and **4.46 ms** across **13** Networks Expansion line pushers.
This sample shows where Slimefun processing occurs, but does not prove that
the server is exceeding a 50 ms whole-server MSPT budget.

For meaningful optimization comparisons, capture several `/sf tick top`
samples before and after a change, with the same machine count, loaded
chunks, server version and player workload. Use a whole-server profiler such
as spark separately when investigating server-wide MSPT/TPS.

These clarifications do not change the sampling frequency, aggregation,
ticker scheduling, rating thresholds, or any machine behavior.
