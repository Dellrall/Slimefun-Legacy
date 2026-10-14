package io.github.thebusybiscuit.slimefun4.core.services.stability;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctor;
import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctorReport;
import java.util.List;
import java.util.function.IntConsumer;
import org.bukkit.plugin.RegisteredServiceProvider;
import org.bukkit.plugin.ServicePriority;
import org.bukkit.plugin.ServicesManager;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.ServerMock;
import org.mockbukkit.mockbukkit.plugin.PluginMock;

/** Covers the public name helper used by addon status after its provider list has been captured. */
class TestAddonDoctorStatusNames {

    private ServerMock server;
    private PluginMock core;
    private ServicesManager services;
    private AddonDoctorService doctor;

    @BeforeEach
    void setUp() {
        server = MockBukkit.mock();
        core = MockBukkit.createMockPlugin("DoctorCore");
        services = server.getServicesManager();
        doctor = new AddonDoctorService(core);
    }

    @AfterEach
    void tearDown() {
        MockBukkit.unmock();
    }

    @Test
    void withdrawnRegistrationUsesOwnerFallbackWithoutCallingTheProvider() {
        TestProvider provider = register("Provider display", core);
        RegisteredServiceProvider<AddonDoctor> captured = registrationOf(provider);
        services.unregister(AddonDoctor.class, provider);

        assertTrue(core.isEnabled());
        assertEquals(core.getName(), doctor.getProviderName(captured));
        assertEquals(0, provider.nameCalls);
        assertEquals(0, provider.runCalls);
    }

    @Test
    void disabledOwnerUsesFallbackWithoutCallingTheProvider() {
        PluginMock owner = MockBukkit.createMockPlugin("DisabledOwner");
        TestProvider provider = register("Provider display", owner);
        RegisteredServiceProvider<AddonDoctor> captured = registrationOf(provider);
        server.getPluginManager().disablePlugin(owner);

        assertFalse(owner.isEnabled());
        assertEquals(owner.getName(), doctor.getProviderName(captured));
        assertEquals(0, provider.nameCalls);
        assertEquals(0, provider.runCalls);
    }

    @Test
    void reregisteringTheSameImplementationDoesNotReviveTheCapturedNameHandle() {
        TestProvider provider = register("Provider display", core);
        RegisteredServiceProvider<AddonDoctor> captured = registrationOf(provider);
        services.unregister(AddonDoctor.class, provider);
        services.register(AddonDoctor.class, provider, core, ServicePriority.Normal);
        RegisteredServiceProvider<AddonDoctor> renewed = registrationOf(provider);

        assertNotSame(captured, renewed);
        assertEquals(core.getName(), doctor.getProviderName(captured));
        assertEquals(0, provider.nameCalls);
        assertEquals("Provider display", doctor.getProviderName(renewed));
        assertEquals(1, provider.nameCalls);
    }

    @Test
    void anUnregisteredLookalikeHandleCannotInvokeAnOtherwiseLiveProvider() {
        TestProvider provider = register("Provider display", core);
        RegisteredServiceProvider<AddonDoctor> lookalike =
                new RegisteredServiceProvider<>(AddonDoctor.class, provider, ServicePriority.Normal, core);

        assertNotSame(registrationOf(provider), lookalike);
        assertEquals(core.getName(), doctor.getProviderName(lookalike));
        assertEquals(0, provider.nameCalls);
        assertEquals("Provider display", doctor.getProviderName(registrationOf(provider)));
        assertEquals(1, provider.nameCalls);
    }

    @Test
    void withdrawalInsideTheNameCallbackReturnsTheOwnerFallback() {
        TestProvider provider = register("Withdrawn display", core);
        RegisteredServiceProvider<AddonDoctor> captured = registrationOf(provider);
        provider.onName = call -> services.unregister(AddonDoctor.class, provider);

        assertEquals(core.getName(), doctor.getProviderName(captured));
        assertEquals(1, provider.nameCalls);
        assertTrue(core.isEnabled());
        assertEquals(core.getName(), doctor.getProviderName(captured));
        assertEquals(1, provider.nameCalls, "A second lookup must not call the withdrawn provider again");
    }

    @Test
    void disablingInsideTheNameCallbackReturnsTheOwnerFallback() {
        PluginMock owner = MockBukkit.createMockPlugin("SelfDisablingOwner");
        TestProvider provider = register("Disabled display", owner);
        RegisteredServiceProvider<AddonDoctor> captured = registrationOf(provider);
        provider.onName = call -> server.getPluginManager().disablePlugin(owner);

        assertEquals(owner.getName(), doctor.getProviderName(captured));
        assertFalse(owner.isEnabled());
        assertEquals(1, provider.nameCalls);
    }

    @Test
    void renewalInsideTheNameCallbackDoesNotMakeTheOldHandleCurrent() {
        TestProvider provider = register("Renewed display", core);
        RegisteredServiceProvider<AddonDoctor> captured = registrationOf(provider);
        provider.onName = call -> {
            if (call == 1) {
                services.unregister(AddonDoctor.class, provider);
                services.register(AddonDoctor.class, provider, core, ServicePriority.Normal);
            }
        };

        assertEquals(core.getName(), doctor.getProviderName(captured));
        RegisteredServiceProvider<AddonDoctor> renewed = registrationOf(provider);
        assertNotSame(captured, renewed);
        assertEquals("Renewed display", doctor.getProviderName(renewed));
        assertEquals(2, provider.nameCalls);
    }

    @Test
    void statusStyleListingSkipsANameWithdrawnByAnEarlierDisplayCallback() {
        assertStatusStyleListing(false);
    }

    @Test
    void statusStyleListingSkipsANameDisabledByAnEarlierDisplayCallback() {
        assertStatusStyleListing(true);
    }

    private void assertStatusStyleListing(boolean disableOwner) {
        PluginMock owner = MockBukkit.createMockPlugin("StatusOwner");
        TestProvider first = register("A first", core);
        TestProvider victim = register("B removed", owner);
        TestProvider healthy = register("C healthy", core);
        first.onName = call -> {
            if (call == 2) {
                if (disableOwner) {
                    server.getPluginManager().disablePlugin(owner);
                } else {
                    services.unregister(AddonDoctor.class, victim);
                }
            }
        };

        List<RegisteredServiceProvider<AddonDoctor>> captured = doctor.getProviders();
        assertEquals(3, captured.size());
        // Mirror DoctorCommand's status loop without invoking a scan or repair.
        List<String> displayed = captured.stream().map(doctor::getProviderName).toList();

        assertEquals(List.of("A first", owner.getName(), "C healthy"), displayed);
        assertEquals(1, victim.nameCalls, "Only the original listing may query the removed provider");
        assertEquals(2, first.nameCalls);
        assertEquals(2, healthy.nameCalls);
        assertEquals(!disableOwner, owner.isEnabled());
        assertEquals(0, first.runCalls + victim.runCalls + healthy.runCalls);
    }

    private TestProvider register(String name, PluginMock owner) {
        TestProvider provider = new TestProvider(name);
        services.register(AddonDoctor.class, provider, owner, ServicePriority.Normal);
        return provider;
    }

    private RegisteredServiceProvider<AddonDoctor> registrationOf(AddonDoctor provider) {
        return services.getRegistrations(AddonDoctor.class).stream()
                .filter(registration -> registration.getProvider() == provider)
                .findFirst()
                .orElseThrow();
    }

    private static final class TestProvider implements AddonDoctor {
        private final String name;
        private IntConsumer onName = call -> {};
        private int nameCalls;
        private int runCalls;

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
            runCalls++;
            return new AddonDoctorReport(name, repair, 1, 0, 0, 0, List.of());
        }
    }
}
