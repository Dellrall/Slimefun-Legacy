package io.github.thebusybiscuit.slimefun4.core.networks.cargo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.bukkit.Location;
import org.junit.jupiter.api.Test;

/** Regression coverage for Cargo frequency parsing and diagnostic hot paths. */
class CargoNetFrequencyTest {

    @Test
    void commonSingleDigitFrequenciesRetainTheirRoutingChannels() {
        // Repeat real channel values to cover the frequently executed fast path.
        for (int i = 0; i < 100_000; i++) {
            int frequency = i % 10;
            assertEquals(frequency, CargoNet.parseFrequency(Integer.toString(frequency)));
        }
    }

    @Test
    void legacyMultiDigitAndLeadingZeroFrequenciesStillParse() {
        assertEquals(0, CargoNet.parseFrequency("000"));
        assertEquals(15, CargoNet.parseFrequency("15"));
        assertEquals(15, CargoNet.parseFrequency("0015"));
        assertEquals(16, CargoNet.parseFrequency("16"));
        assertEquals(Integer.MAX_VALUE, CargoNet.parseFrequency("2147483647"));
    }

    @Test
    void malformedAndOverflowFrequenciesCannotAbortNetworkScan() {
        assertEquals(-1, CargoNet.parseFrequency(null));
        assertEquals(-1, CargoNet.parseFrequency(""));
        assertEquals(-1, CargoNet.parseFrequency("bad"));
        assertEquals(-1, CargoNet.parseFrequency("1.5"));
        assertEquals(-1, CargoNet.parseFrequency(" 1"));
        assertEquals(-1, CargoNet.parseFrequency("2147483648"));
        assertEquals(-1, CargoNet.parseFrequency("99999999999999999999999999999999"));
    }

    @Test
    void invalidFrequencyWarningsAreDeduplicatedByNodeAndValue() {
        Map<Location, String> reported = new ConcurrentHashMap<>();
        Location first = new Location(null, 1, 64, 1);
        Location second = new Location(null, 2, 64, 1);

        assertTrue(CargoNet.shouldReportInvalidFrequency(reported, first, "broken"));
        assertFalse(CargoNet.shouldReportInvalidFrequency(reported, first, "broken"));
        assertTrue(CargoNet.shouldReportInvalidFrequency(reported, second, "broken"));
        assertTrue(CargoNet.shouldReportInvalidFrequency(reported, first, "oversized"));
        assertFalse(CargoNet.shouldReportInvalidFrequency(reported, first, "oversized"));

        // A valid saved frequency or a removed node clears its warning state.
        reported.remove(first);
        assertTrue(CargoNet.shouldReportInvalidFrequency(reported, first, "oversized"));
    }
}
