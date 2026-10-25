package io.github.thebusybiscuit.slimefun4.core.ticker;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class FairTickerBatchTest {

    @Test
    void rotatesTheWindowWithoutStarvingLaterMachines() {
        FairTickerBatch<Integer> budget = new FairTickerBatch<>(List.of(0, 1, 2, 3, 4, 5, 6));
        assertEquals(List.of(0, 1, 2), budget.next(3));
        assertEquals(List.of(3, 4, 5), budget.next(3));
        assertEquals(List.of(6, 0, 1), budget.next(3));
        assertEquals(List.of(2, 3, 4), budget.next(3));
    }

    @Test
    void largeExistingBaseEventuallyServicesEveryRegisteredTicker() {
        List<Integer> machines = new ArrayList<>(7_454);
        for (int i = 0; i < 7_454; i++) {
            machines.add(i);
        }

        FairTickerBatch<Integer> budget = new FairTickerBatch<>(machines);
        Set<Integer> observed = new HashSet<>();
        for (int i = 0; i < 15; i++) {
            List<Integer> current = budget.next(512);
            assertEquals(512, current.size());
            observed.addAll(current);
        }
        assertEquals(7_454, observed.size(), "All ticker registrations must be served eventually");
    }

    @Test
    void quotaAboveRegistrationCountStillRunsAllOnce() {
        FairTickerBatch<String> budget = new FairTickerBatch<>(List.of("A", "B"));
        assertEquals(List.of("A", "B"), budget.next(512));
        assertEquals(List.of("A", "B"), budget.next(512));
    }

    @Test
    void emptyChunksDoNotScheduleAnything() {
        FairTickerBatch<String> budget = new FairTickerBatch<>(List.of());
        assertTrue(budget.next(32).isEmpty());
    }

    @Test
    void neverAcceptsNonpositiveQuotasOrZeroLengthEnforcement() {
        FairTickerBatch<Integer> budget = new FairTickerBatch<>(List.of(1, 2, 3));
        assertThrows(IllegalArgumentException.class, () -> budget.next(0));
        assertThrows(IllegalArgumentException.class, () -> budget.next(-1));
    }

    @Test
    void snapshotKeepsItsOriginalListAfterCallerChangesRegistrations() {
        List<Integer> mutable = new ArrayList<>(List.of(1, 2, 3));
        FairTickerBatch<Integer> budget = new FairTickerBatch<>(mutable);
        mutable.add(4);
        assertEquals(3, budget.size());
        assertEquals(List.of(1, 2, 3), budget.next(3));
    }
}
