package io.github.thebusybiscuit.slimefun4.core.services.stability;

import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctor;
import io.github.thebusybiscuit.slimefun4.api.diagnostics.AddonDoctorReport;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import javax.annotation.Nonnull;
import org.bukkit.Bukkit;
import org.bukkit.plugin.RegisteredServiceProvider;
import org.bukkit.plugin.java.JavaPlugin;

/** Discovers and safely invokes addon-provided doctor services. */
public final class AddonDoctorService {

    private final JavaPlugin plugin;

    public AddonDoctorService(@Nonnull JavaPlugin plugin) {
        this.plugin = plugin;
    }

    @Nonnull
    public List<RegisteredServiceProvider<AddonDoctor>> getProviders() {
        List<RegisteredServiceProvider<AddonDoctor>> providers =
                new ArrayList<>(Bukkit.getServicesManager().getRegistrations(AddonDoctor.class));
        providers.removeIf(provider -> !isProviderEnabled(provider));
        // A comparator must not repeatedly invoke mutable third-party code. Resolve each
        // registration once for this listing, retaining the existing safe fallback behavior.
        Map<RegisteredServiceProvider<AddonDoctor>, String> names = new IdentityHashMap<>();
        for (RegisteredServiceProvider<AddonDoctor> provider : providers) {
            if (isProviderEnabled(provider)) {
                names.put(provider, getProviderName(provider));
            }
        }
        // A name callback may disable its own plugin or another provider from this snapshot.
        providers.removeIf(provider -> !names.containsKey(provider) || !isProviderEnabled(provider));
        providers.sort(Comparator.comparing(names::get, String.CASE_INSENSITIVE_ORDER));
        return providers;
    }

    /** Returns a provider name without trusting third-party code to behave during status output. */
    @Nonnull
    public String getProviderName(@Nonnull RegisteredServiceProvider<AddonDoctor> registration) {
        String fallback = registration.getPlugin() == null
                ? "Unknown addon"
                : registration.getPlugin().getName();
        try {
            String name = registration.getProvider().getAddonName();
            if (name != null && !name.isBlank()) {
                return name.trim();
            }
        } catch (Throwable throwable) {
            plugin.getLogger().log(Level.FINE, "Addon doctor name lookup failed for " + fallback, throwable);
        }
        return fallback;
    }

    @Nonnull
    public List<AddonDoctorReport> runAll(boolean repair) {
        List<AddonDoctorReport> reports = new ArrayList<>();
        for (RegisteredServiceProvider<AddonDoctor> registration : getProviders()) {
            // An earlier provider can disable a later provider after the list was captured.
            if (!isProviderEnabled(registration)) {
                continue;
            }
            AddonDoctor provider = registration.getProvider();
            String addonName = getProviderName(registration);
            String pluginName = registration.getPlugin() == null
                    ? "unknown plugin"
                    : registration.getPlugin().getName();
            // The name callback above is third-party code too; it may disable this plugin.
            if (!isProviderEnabled(registration)) {
                continue;
            }
            try {
                AddonDoctorReport report = provider.runDoctor(repair);
                if (report == null) {
                    throw new IllegalStateException("Addon doctor returned null");
                }
                reports.add(report);
            } catch (Throwable throwable) {
                plugin.getLogger()
                        .log(
                                Level.WARNING,
                                "Addon doctor failed for " + addonName + " (provider " + pluginName + ")",
                                throwable);
                reports.add(new AddonDoctorReport(
                        addonName,
                        repair,
                        0L,
                        1L,
                        0L,
                        1L,
                        List.of("Provider threw " + throwable.getClass().getSimpleName() + ": "
                                + String.valueOf(throwable.getMessage()))));
            }
        }
        return reports;
    }

    private static boolean isProviderEnabled(@Nonnull RegisteredServiceProvider<AddonDoctor> registration) {
        return registration.getPlugin() != null && registration.getPlugin().isEnabled();
    }
}
