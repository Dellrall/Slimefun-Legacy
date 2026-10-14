package io.github.thebusybiscuit.slimefun4.core.services.stability;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctor;
import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctorReport;
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntConsumer;
import org.bukkit.plugin.RegisteredServiceProvider;
import org.bukkit.plugin.ServicePriority;
import org.bukkit.plugin.ServicesManager;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.plugin.PluginMock;

/** Exercises synchronous service withdrawal while the owning plugin remains enabled. */
class TestAddonDoctorRegistrations {

    private PluginMock core;
    private ServicesManager services;
    private AddonDoctorService doctor;

    @BeforeEach
    void setUp() {
        services = MockBukkit.mock().getServicesManager();
        core = MockBukkit.createMockPlugin("DoctorCore");
        doctor = new AddonDoctorService(core);
    }

    @AfterEach
    void tearDown() {
        MockBukkit.unmock();
    }

    @Test
    void anEarlierScanCannotInvokeAnUnregisteredProvider() {
        assertUnregisteredDuringRun(false);
    }

    @Test
    void anEarlierRepairCannotInvokeAnUnregisteredProvider() {
        assertUnregisteredDuringRun(true);
    }

    private void assertUnregisteredDuringRun(boolean repair) {
        PluginMock addon = MockBukkit.createMockPlugin("EnabledAddon");
        TestProvider first = register("A first", core);
        TestProvider withdrawn = register("B withdrawn", addon);
        TestProvider healthy = register("C healthy", core);
        first.onRun = () -> services.unregister(AddonDoctor.class, withdrawn);

        List<AddonDoctorReport> reports = doctor.runAll(repair);

        assertTrue(addon.isEnabled(), "Service withdrawal does not disable the plugin");
        assertEquals(List.of("A first", "C healthy"), reportNames(reports));
        assertTrue(withdrawn.modes.isEmpty(), "Do not invoke the detached, unregistered provider");
        assertEquals(1, withdrawn.nameCalls, "Only the original listing may query the withdrawn provider");
        assertEquals(List.of(repair), first.modes);
        assertEquals(List.of(repair), healthy.modes);
        assertTrue(reports.stream().allMatch(report -> report.isRepairMode() == repair));
    }

    @Test
    void unregisteringDuringThePreScanNameLookupPreventsTheScan() {
        assertUnregisteredDuringPreRunName(false);
    }

    @Test
    void unregisteringDuringThePreRepairNameLookupPreventsTheRepair() {
        assertUnregisteredDuringPreRunName(true);
    }

    private void assertUnregisteredDuringPreRunName(boolean repair) {
        PluginMock addon = MockBukkit.createMockPlugin("SelfWithdrawingAddon");
        TestProvider withdrawn = register("A withdrawn", addon);
        TestProvider healthy = register("B healthy", core);
        withdrawn.onName = call -> {
            if (call == 2) {
                services.unregister(AddonDoctor.class, withdrawn);
            }
        };

        List<AddonDoctorReport> reports = doctor.runAll(repair);

        assertTrue(addon.isEnabled());
        assertEquals(2, withdrawn.nameCalls);
        assertTrue(withdrawn.modes.isEmpty());
        assertEquals(List.of("B healthy"), reportNames(reports));
        assertEquals(List.of(repair), healthy.modes);
    }

    @Test
    void selfUnregistrationDuringListingDoesNotEscapeTheListing() {
        TestProvider withdrawn = register("A withdrawn", core);
        TestProvider healthy = register("B healthy", core);
        withdrawn.onName = call -> services.unregister(AddonDoctor.class, withdrawn);

        assertEquals(List.of(healthy), listedProviders());
        assertTrue(core.isEnabled());
        assertEquals(1, withdrawn.nameCalls);
        assertTrue(withdrawn.modes.isEmpty());
        assertTrue(healthy.modes.isEmpty(), "Listing must not run a scan or repair");
    }

    @Test
    void anEarlierListingCallbackCannotQueryAProviderItUnregistered() {
        // Different priorities establish callback order independently of service insertion order.
        TestProvider first = register("A first", core, ServicePriority.Highest);
        TestProvider withdrawn = register("B withdrawn", core, ServicePriority.Normal);
        TestProvider healthy = register("C healthy", core, ServicePriority.Lowest);
        first.onName = call -> services.unregister(AddonDoctor.class, withdrawn);

        assertEquals(List.of(first, healthy), listedProviders());
        assertEquals(0, withdrawn.nameCalls);
        assertTrue(core.isEnabled());
    }

    @Test
    void aLaterListingCallbackRemovesAnAlreadyNamedRegistration() {
        TestProvider withdrawn = register("A withdrawn", core, ServicePriority.Highest);
        TestProvider remover = register("B remover", core, ServicePriority.Normal);
        TestProvider healthy = register("C healthy", core, ServicePriority.Lowest);
        remover.onName = call -> services.unregister(AddonDoctor.class, withdrawn);

        assertEquals(List.of(remover, healthy), listedProviders());
        assertEquals(1, withdrawn.nameCalls);
        assertTrue(core.isEnabled());
    }

    @Test
    void withdrawingAllServicesForAnEnabledOwnerSkipsEveryStaleRepair() {
        PluginMock addon = MockBukkit.createMockPlugin("WithdrawingOwner");
        TestProvider first = register("A first", core);
        TestProvider withdrawnOne = register("B withdrawn", addon);
        TestProvider withdrawnTwo = register("C withdrawn", addon);
        TestProvider healthy = register("D healthy", core);
        first.onRun = () -> services.unregisterAll(addon);

        assertEquals(List.of("A first", "D healthy"), reportNames(doctor.runAll(true)));
        assertTrue(addon.isEnabled());
        assertTrue(withdrawnOne.modes.isEmpty());
        assertTrue(withdrawnTwo.modes.isEmpty());
        assertEquals(List.of(true), healthy.modes);
    }

    @Test
    void replacementProviderWaitsUntilTheNextPass() {
        TestProvider first = register("A first", core);
        TestProvider old = register("B replaceable", core);
        TestProvider replacement = new TestProvider("B replaceable");
        TestProvider healthy = register("C healthy", core);
        first.onRun = () -> {
            services.unregister(AddonDoctor.class, old);
            services.register(AddonDoctor.class, replacement, core, ServicePriority.Normal);
            first.onRun = () -> {};
        };

        assertEquals(List.of("A first", "C healthy"), reportNames(doctor.runAll(true)));
        assertTrue(old.modes.isEmpty());
        assertTrue(replacement.modes.isEmpty());
        assertEquals(0, replacement.nameCalls, "A new provider must not be added to an in-progress pass");

        assertEquals(List.of("A first", "B replaceable", "C healthy"), reportNames(doctor.runAll(false)));
        assertEquals(List.of(false), replacement.modes);
        assertTrue(old.modes.isEmpty());
        assertEquals(List.of(true, false), healthy.modes);
    }

    @Test
    void reregisteringTheSameObjectDoesNotReviveItsOldRegistration() {
        TestProvider first = register("A first", core);
        TestProvider renewed = register("B renewed", core);
        RegisteredServiceProvider<AddonDoctor> before = registrationOf(renewed);
        first.onRun = () -> {
            services.unregister(AddonDoctor.class, renewed);
            services.register(AddonDoctor.class, renewed, core, ServicePriority.Normal);
            first.onRun = () -> {};
        };

        assertEquals(List.of("A first"), reportNames(doctor.runAll(true)));
        assertNotSame(before, registrationOf(renewed), "This fixture must create a new registration");
        assertTrue(renewed.modes.isEmpty(), "Provider identity alone must not revive the old registration");

        assertEquals(List.of("A first", "B renewed"), reportNames(doctor.runAll(false)));
        assertEquals(List.of(false), renewed.modes);
    }

    @Test
    void providerFailureAfterUnregisteringAnotherStillLeavesHealthyProvidersRunning() {
        TestProvider failing = register("A failing", core);
        TestProvider withdrawn = register("B withdrawn", core);
        TestProvider healthy = register("C healthy", core);
        failing.onRun = () -> {
            services.unregister(AddonDoctor.class, withdrawn);
            throw new IllegalStateException("Failure after service withdrawal");
        };

        List<AddonDoctorReport> reports = doctor.runAll(false);

        assertEquals(List.of("A failing", "C healthy"), reportNames(reports));
        assertTrue(withdrawn.modes.isEmpty());
        assertEquals(List.of(false), healthy.modes);
    }

    @Test
    void equalDisplayNamesDoNotHideDistinctLiveRegistrations() {
        TestProvider first = register("Shared name", core, ServicePriority.Highest);
        TestProvider second = register("Shared name", core, ServicePriority.Lowest);

        assertEquals(List.of("Shared name", "Shared name"), reportNames(doctor.runAll(false)));
        assertEquals(List.of(false), first.modes);
        assertEquals(List.of(false), second.modes);
    }

    private List<AddonDoctor> listedProviders() {
        return doctor.getProviders().stream()
                .map(RegisteredServiceProvider::getProvider)
                .toList();
    }

    private RegisteredServiceProvider<AddonDoctor> registrationOf(AddonDoctor provider) {
        return services.getRegistrations(AddonDoctor.class).stream()
                .filter(registration -> registration.getProvider() == provider)
                .findFirst()
                .orElseThrow();
    }

    private TestProvider register(String name, PluginMock owner) {
        return register(name, owner, ServicePriority.Normal);
    }

    private TestProvider register(String name, PluginMock owner, ServicePriority priority) {
        TestProvider provider = new TestProvider(name);
        services.register(AddonDoctor.class, provider, owner, priority);
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
