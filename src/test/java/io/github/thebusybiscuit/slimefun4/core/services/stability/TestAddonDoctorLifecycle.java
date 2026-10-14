package io.github.thebusybiscuit.slimefun4.core.services.stability;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctor;
import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctorReport;
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntConsumer;
import org.bukkit.plugin.ServicePriority;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.ServerMock;
import org.mockbukkit.mockbukkit.plugin.PluginMock;

/** Regression coverage for synchronous provider disablement during a Doctor pass. */
class TestAddonDoctorLifecycle {

    private ServerMock server;
    private PluginMock core;
    private AddonDoctorService service;

    @BeforeEach
    void setUp() {
        server = MockBukkit.mock();
        core = MockBukkit.createMockPlugin("DoctorCore");
        service = new AddonDoctorService(core);
    }

    @AfterEach
    void tearDown() {
        MockBukkit.unmock();
    }

    @Test
    void anEarlierScanCannotInvokeAnAddonItDisabled() {
        assertEarlierProviderDisablement(false);
    }

    @Test
    void anEarlierRepairCannotInvokeAnAddonItDisabled() {
        assertEarlierProviderDisablement(true);
    }

    private void assertEarlierProviderDisablement(boolean repair) {
        PluginMock addon = MockBukkit.createMockPlugin("LaterAddon");
        TestProvider first = register("A first", core);
        TestProvider later = register("B later", addon);
        TestProvider healthy = register("C healthy", core);
        first.onRun = () -> server.getPluginManager().disablePlugin(addon);

        List<AddonDoctorReport> reports = service.runAll(repair);

        assertFalse(addon.isEnabled());
        assertEquals(List.of("A first", "C healthy"), reportNames(reports));
        assertEquals(List.of(repair), first.modes);
        assertEquals(List.of(repair), healthy.modes);
        assertTrue(later.modes.isEmpty(), "Never invoke a disabled provider from the captured list");
        assertEquals(1, later.nameCalls, "Only the original listing may query this provider's name");
        assertTrue(reports.stream().allMatch(report -> report.isRepairMode() == repair));
    }

    @Test
    void disablingDuringThePreScanNameLookupPreventsTheScan() {
        assertPreRunNameDisablement(false);
    }

    @Test
    void disablingDuringThePreRepairNameLookupPreventsTheRepair() {
        assertPreRunNameDisablement(true);
    }

    private void assertPreRunNameDisablement(boolean repair) {
        PluginMock addon = MockBukkit.createMockPlugin("SelfDisablingAddon");
        TestProvider changing = register("A changing", addon);
        TestProvider healthy = register("B healthy", core);
        changing.onName = call -> {
            if (call == 2) {
                server.getPluginManager().disablePlugin(addon);
            }
        };

        List<AddonDoctorReport> reports = service.runAll(repair);

        assertFalse(addon.isEnabled());
        assertEquals(2, changing.nameCalls);
        assertTrue(changing.modes.isEmpty(), "A name callback must not permit a disabled repair");
        assertEquals(List.of("B healthy"), reportNames(reports));
        assertEquals(List.of(repair), healthy.modes);
    }

    @Test
    void aProviderDisabledByItsListingNameDoesNotEscapeTheListing() {
        PluginMock addon = MockBukkit.createMockPlugin("ListingAddon");
        TestProvider changing = register("A changing", addon);
        TestProvider healthy = register("B healthy", core);
        changing.onName = call -> server.getPluginManager().disablePlugin(addon);

        List<AddonDoctor> listed = service.getProviders().stream()
                .map(registration -> registration.getProvider()).toList();

        assertFalse(addon.isEnabled());
        assertEquals(List.of(healthy), listed);
        assertEquals(1, changing.nameCalls);
        assertTrue(changing.modes.isEmpty());
        assertTrue(healthy.modes.isEmpty(), "Listing remains read-only");
    }

    @Test
    void aRetainedRegistrationForAnAlreadyDisabledPluginIsNotCalled() {
        PluginMock addon = MockBukkit.createMockPlugin("DisabledAddon");
        server.getPluginManager().disablePlugin(addon);
        // Explicitly retain a service registration after disablement to exercise the filter.
        TestProvider disabled = register("A disabled", addon);
        TestProvider healthy = register("B healthy", core);

        assertEquals(List.of("B healthy"), reportNames(service.runAll(false)));
        assertEquals(0, disabled.nameCalls);
        assertTrue(disabled.modes.isEmpty());
        assertEquals(List.of(false), healthy.modes);
    }

    @Test
    void mutatingTheReturnedListDoesNotUnregisterProviders() {
        TestProvider healthy = register("Healthy", core);
        service.getProviders().clear();

        assertEquals(List.of("Healthy"), reportNames(service.runAll(false)));
        assertEquals(List.of(false), healthy.modes);
    }

    private TestProvider register(String name, PluginMock owner) {
        TestProvider provider = new TestProvider(name);
        server.getServicesManager().register(AddonDoctor.class, provider, owner, ServicePriority.Normal);
        return provider;
    }

    private static List<String> reportNames(List<AddonDoctorReport> reports) {
        return reports.stream().map(AddonDoctorReport::getAddonName).toList();
    }

    private static final class TestProvider implements AddonDoctor {
        private final String name;
        private final List<Boolean> modes = new ArrayList<>();
        private IntConsumer onName = call -> {};
        private Runnable onRun = () -> {};
        private int nameCalls;

        private TestProvider(String name) {
            this.name = name;
        }

        @Override
        public String getAddonName() {
            onName.accept(++nameCalls);
            return name;
        }

        @Override
        public AddonDoctorReport runDoctor(boolean repair) {
            modes.add(repair);
            onRun.run();
            return new AddonDoctorReport(name, repair, 1, 0, 0, 0, List.of());
        }
    }
}
