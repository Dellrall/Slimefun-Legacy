package networksprobe.receipt;

import com.google.gson.JsonObject;
import java.io.InputStream;
import java.nio.file.Files;
import java.util.Properties;
import org.bukkit.Bukkit;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.java.JavaPlugin;

/** Metadata-only companion; the pinned storage fixture retains every operation and assertion. */
public final class PairedStorageReceipt extends JavaPlugin {
    private JsonObject started;
    private String phase;
    private String token;

    @Override
    public void onEnable() {
        try {
            phase = System.getProperty("sfl.paired.phase", "");
            token = System.getProperty("sfl.paired.token", "");
            if (!"disposable".equals(System.getProperty("networks.paired.probe"))
                    || !phase.matches("seed|verify") || !token.matches("[0-9a-f-]{36}")) {
                throw new IllegalStateException("Disposable paired receipt identity is required");
            }
            Plugin core = enabled("Slimefun");
            Plugin networks = enabled("Networks");
            Plugin ie2 = enabled("InfinityExpansion2");
            enabled("PairedIE2StorageProbe");
            Properties properties = new Properties();
            try (InputStream input = ((JavaPlugin) core).getResource("git.properties")) {
                if (input == null) {
                    throw new IllegalStateException("Loaded core source properties are missing");
                }
                properties.load(input);
            }
            started = new JsonObject();
            started.addProperty("schema", 1);
            started.addProperty("phase", phase);
            started.addProperty("token", token);
            started.addProperty("pid", ProcessHandle.current().pid());
            started.addProperty("software", Bukkit.getName());
            started.addProperty("minecraft", Bukkit.getMinecraftVersion());
            started.addProperty("server_version", Bukkit.getVersion());
            started.addProperty("core_source", properties.getProperty("git.source.commit"));
            started.addProperty("core_commit", properties.getProperty("git.commit.id"));
            started.addProperty("core_version", core.getPluginMeta().getVersion());
            started.addProperty("networks_version", networks.getPluginMeta().getVersion());
            started.addProperty("ie2_version", ie2.getPluginMeta().getVersion());
            started.addProperty("primary_thread", Bukkit.isPrimaryThread());
            started.addProperty("status", "READY");
            write("startup.json", started);
            getLogger().info("PAIRED_STORAGE_RECEIPT READY phase=" + phase + " token=" + token);
        } catch (Exception failure) {
            getLogger().severe("PAIRED_STORAGE_RECEIPT FAIL " + failure);
            Bukkit.shutdown();
        }
    }

    @Override
    public void onDisable() {
        if (started == null) {
            return;
        }
        try {
            JsonObject completion = started.deepCopy();
            completion.addProperty("status", "STOPPED");
            completion.addProperty("server_stopping", Bukkit.isStopping());
            write("shutdown.json", completion);
            getLogger().info("PAIRED_STORAGE_RECEIPT STOPPED phase=" + phase + " token=" + token);
        } catch (Exception failure) {
            getLogger().severe("PAIRED_STORAGE_RECEIPT FAIL " + failure);
        }
    }

    private Plugin enabled(String name) {
        Plugin plugin = Bukkit.getPluginManager().getPlugin(name);
        if (plugin == null || !plugin.isEnabled()) {
            throw new IllegalStateException("Required fixture plugin is not enabled: " + name);
        }
        return plugin;
    }

    private void write(String name, JsonObject value) throws Exception {
        Files.createDirectories(getDataFolder().toPath());
        Files.writeString(getDataFolder().toPath().resolve(name), value + "\n");
    }
}
