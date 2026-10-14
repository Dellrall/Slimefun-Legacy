package io.github.thebusybiscuit.slimefun4.core.services.stability;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctor;
import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctorReport;
import java.util.ArrayList;
import java.util.List;
import org.bukkit.plugin.RegisteredServiceProvider;
import org.bukkit.plugin.ServicePriority;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.ServerMock;
import org.mockbukkit.mockbukkit.plugin.PluginMock;

class TestAddonDoctorService {

    private ServerMock server;
    private PluginMock plugin;
    private AddonDoctorService service;

    @BeforeEach
    void setUp() {
        server = MockBukkit.mock();
        plugin = MockBukkit.createMockPlugin();
        service = new AddonDoctorService(plugin);
    }

    @AfterEach
    void tearDown() {
        MockBukkit.unmock();
    }

    @Test
    void resolvesEachNameOncePerListingAndPreservesCaseInsensitiveOrder() {
        TestProvider delta = register("Delta");
        TestProvider alpha = register(" alpha ");
        TestProvider charlie = register("CHARLIE");
        TestProvider bravo = register("bravo");

        List<RegisteredServiceProvider<AddonDoctor>> registrations = service.getProviders();

        assertEquals(List.of(alpha, bravo, charlie, delta), providers(registrations));
        for (TestProvider provider : List.of(delta, alpha, charlie, bravo)) {
            assertEquals(1, provider.nameCalls);
            assertTrue(provider.modes.isEmpty(), "Listing must not run a scan or repair");
        }
    }

    @Test
    void aStatefulNameIsNotReevaluatedDuringSorting() {
        TestProvider delta = register("Delta");
        TestProvider alpha = register("Alpha");
        TestProvider bravo = register("Bravo");
        delta.laterName = "Aardvark";
        alpha.laterName = "Zulu";
        bravo.laterName = "Mango";

        assertEquals(List.of(alpha, bravo, delta), providers(service.getProviders()));
        assertEquals(1, delta.nameCalls);
        assertEquals(1, alpha.nameCalls);
        assertEquals(1, bravo.nameCalls);
    }

    @Test
    void eachNewListingRefreshesTheNameSnapshot() {
        TestProvider zebra = register("Zebra");
        TestProvider alpha = register("Alpha");
        zebra.laterName = "Aardvark";
        alpha.laterName = "Zulu";

        assertEquals(List.of(alpha, zebra), providers(service.getProviders()));
        assertEquals(List.of(zebra, alpha), providers(service.getProviders()));
        assertEquals(2, zebra.nameCalls);
        assertEquals(2, alpha.nameCalls);
    }

    @Test
    void missingAndFailingNamesKeepTheirPluginFallback() {
        TestProvider broken = register("Broken");
        broken.failName = true;
        TestProvider blank = register("   ");
        TestProvider missing = register(null);
        TestProvider valid = register("Good");

        List<RegisteredServiceProvider<AddonDoctor>> registrations = service.getProviders();

        assertEquals(4, registrations.size());
        for (TestProvider provider : List.of(broken, blank, missing, valid)) {
            assertEquals(1, provider.nameCalls);
        }
        for (RegisteredServiceProvider<AddonDoctor> registration : registrations) {
            assertEquals(registration.getProvider() == valid ? "Good" : plugin.getName(),
                    service.getProviderName(registration));
        }
    }

    @Test
    void dryRunAndRepairFlagsAreForwardedWithoutExtraProviderRuns() {
        TestProvider beta = register("Beta");
        TestProvider alpha = register("Alpha");

        List<AddonDoctorReport> scan = service.runAll(false);
        List<AddonDoctorReport> repair = service.runAll(true);

        assertEquals(List.of("Alpha", "Beta"), scan.stream().map(AddonDoctorReport::getAddonName).toList());
        assertEquals(List.of(false, true), alpha.modes);
        assertEquals(List.of(false, true), beta.modes);
        assertTrue(scan.stream().noneMatch(AddonDoctorReport::isRepairMode));
        assertTrue(repair.stream().allMatch(AddonDoctorReport::isRepairMode));
    }

    @Test
    void failingOrNullReportsDoNotBlockHealthyProviders() {
        TestProvider broken = register("Broken");
        broken.failRun = true;
        TestProvider missing = register("Missing");
        missing.nullReport = true;
        TestProvider healthy = register("Healthy");

        List<AddonDoctorReport> reports = service.runAll(false);

        assertEquals(3, reports.size());
        assertEquals(List.of(false), broken.modes);
        assertEquals(List.of(false), missing.modes);
        assertEquals(List.of(false), healthy.modes);
        assertEquals(2, reports.stream().filter(r -> r.getDetails().stream()
                .anyMatch(line -> line.startsWith("Provider threw"))).count());
        assertFalse(reports.stream().filter(r -> r.getAddonName().equals("Healthy"))
                .findFirst().orElseThrow().isRepairMode());
    }

    private TestProvider register(String name) {
        TestProvider provider = new TestProvider(name);
        server.getServicesManager().register(AddonDoctor.class, provider, plugin, ServicePriority.Normal);
        return provider;
    }

    private static List<AddonDoctor> providers(List<RegisteredServiceProvider<AddonDoctor>> registrations) {
        return registrations.stream().map(RegisteredServiceProvider::getProvider).toList();
    }

    private static final class TestProvider implements AddonDoctor {
        private final String name;
        private final List<Boolean> modes = new ArrayList<>();
        private String laterName;
        private int nameCalls;
        private boolean failName;
        private boolean failRun;
        private boolean nullReport;

        private TestProvider(String name) {
            this.name = name;
        }

        @Override
        public String getAddonName() {
            nameCalls++;
            if (failName) {
                throw new IllegalStateException("Synthetic name lookup failure");
            }
            return nameCalls > 1 && laterName != null ? laterName : name;
        }

        @Override
        public AddonDoctorReport runDoctor(boolean repair) {
            modes.add(repair);
            if (failRun) {
                throw new IllegalStateException("Synthetic scan failure");
            }
            return nullReport ? null : new AddonDoctorReport(name, repair, 1, 0, 0, 0, List.of());
        }
    }
}
