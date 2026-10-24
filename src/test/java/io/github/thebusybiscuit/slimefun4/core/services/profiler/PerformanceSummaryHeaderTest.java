package io.github.thebusybiscuit.slimefun4.core.services.profiler;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** Profiler output must not present accumulated Slimefun work as whole-server MSPT. */
class PerformanceSummaryHeaderTest {

    @Test
    void tickerHeaderClearlyLabelsSampledWorkAndConfiguredCadence() {
        SlimefunProfiler profiler = new SlimefunProfiler() {
            @Override
            public int getTickRate() {
                return 10;
            }

            @Override
            protected Map<String, Long> getByItem() {
                return Map.of();
            }

            @Override
            protected Map<String, Long> getByChunk() {
                return Map.of();
            }

            @Override
            protected Map<String, Long> getByPlugin() {
                return Map.of();
            }
        };

        try {
            List<String> lines = new ArrayList<>();
            PerformanceSummary summary = new PerformanceSummary(profiler, 51_370_000L, 1818);
            summary.send(new PerformanceInspector() {
                @Override
                public boolean isValid() {
                    return true;
                }

                @Override
                public void sendMessage(String line) {
                    lines.add(line);
                }

                @Override
                public boolean isVerbose() {
                    return false;
                }

                @Override
                public SummaryOrderType getOrderType() {
                    return SummaryOrderType.HIGHEST;
                }
            });

            assertTrue(lines.stream().anyMatch(line -> line.contains("Total sampled ticker work: ")
                    && line.contains("51.37")), "Cumulative work should preserve its measured total");
            assertTrue(lines.stream().anyMatch(line -> line.contains("Ticker interval: ")
                    && line.contains("10 ticks")
                    && line.contains("at 20 TPS")), "Configured tick cadence is not measured runtime");
            assertTrue(lines.stream().anyMatch(line -> line.contains("not full-server MSPT or TPS")));
            assertTrue(lines.stream().anyMatch(line -> line.contains("Performance rating: ")),
                    "Existing performance rating remains available");
            assertFalse(lines.stream().anyMatch(line -> line.contains("Total tick time: ")
                    || line.contains("Ticker runtime: ")),
                    "Ambiguous historical headers must not be reintroduced");
        } finally {
            profiler.kill();
        }
    }
}
