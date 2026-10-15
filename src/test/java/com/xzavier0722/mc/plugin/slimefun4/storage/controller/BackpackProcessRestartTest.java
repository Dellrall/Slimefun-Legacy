package com.xzavier0722.mc.plugin.slimefun4.storage.controller;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.File;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

/** Separate JVMs and disposable SQLite files, not Minecraft clients or a power-loss simulation. */
class BackpackProcessRestartTest {
    @TempDir
    Path directory;

    enum Boundary {
        CLEAN_SHUTDOWN(0),
        BEFORE_WRITE(73),
        AFTER_WRITE_BEFORE_ACK(74),
        AFTER_ACK(75);

        final int exitCode;

        Boundary(int exitCode) {
            this.exitCode = exitCode;
        }
    }

    @ParameterizedTest
    @EnumSource(Boundary.class)
    void freshProcessReadsTheExpectedCommittedStateWithoutRewritingOtherRows(Boundary boundary) throws Exception {
        String nonce = UUID.randomUUID().toString();
        Set<Long> pids = new LinkedHashSet<>();
        pids.add(run("SEED", boundary, nonce, 0));
        pids.add(run("WRITE", boundary, nonce, boundary.exitCode));
        pids.add(run("VERIFY", boundary, nonce, 0));
        assertEquals(3, pids.size(), "Seeding, writing and verification must use distinct JVMs");
    }

    private long run(String phase, Boundary boundary, String nonce, int expectedExit) throws Exception {
        Path log = directory.resolve(phase.toLowerCase() + ".log");
        String executable = System.getProperty("os.name").startsWith("Windows") ? "java.exe" : "java";
        Process process = new ProcessBuilder(
                        Path.of(System.getProperty("java.home"), "bin", executable)
                                .toString(),
                        "-Xmx384m",
                        "-Dfile.encoding=UTF-8",
                        "-cp",
                        runtimeClasspath(),
                        BackpackProcessProbe.class.getName(),
                        directory.toAbsolutePath().toString(),
                        phase,
                        boundary.name(),
                        nonce)
                .redirectErrorStream(true)
                .redirectOutput(log.toFile())
                .start();
        try {
            assertTrue(process.waitFor(60, TimeUnit.SECONDS), () -> "Timed out in " + phase + ":\n" + readLog(log));
            String output = readLog(log);
            assertEquals(expectedExit, process.exitValue(), output);
            String marker = "BACKPACK_PROCESS:" + nonce + ":" + phase + ":" + process.pid();
            assertTrue(output.lines().anyMatch(marker::equals), output);
            assertFalse(process.isAlive());
            return process.pid();
        } finally {
            if (process.isAlive()) {
                process.destroyForcibly();
                assertTrue(process.waitFor(10, TimeUnit.SECONDS), "Failed to reap the disposable child JVM");
            }
        }
    }

    private static String readLog(Path log) {
        try {
            return Files.readString(log);
        } catch (Exception failure) {
            return "Could not read child log: " + failure;
        }
    }

    private static String runtimeClasspath() throws Exception {
        Set<String> entries = new LinkedHashSet<>();
        // Gradle's worker java.class.path is not necessarily the test runtime classpath.
        for (ClassLoader loader = BackpackProcessRestartTest.class.getClassLoader();
                loader != null;
                loader = loader.getParent()) {
            if (loader instanceof URLClassLoader urls) {
                for (var url : urls.getURLs()) {
                    if (url.getProtocol().equals("file")) {
                        entries.add(Path.of(url.toURI()).toString());
                    }
                }
            }
        }
        entries.addAll(Arrays.asList(System.getProperty("java.class.path").split(File.pathSeparator)));
        entries.add(Path.of(BackpackProcessProbe.class
                        .getProtectionDomain()
                        .getCodeSource()
                        .getLocation()
                        .toURI())
                .toString());
        return entries.stream().filter(entry -> !entry.isBlank()).collect(Collectors.joining(File.pathSeparator));
    }
}
