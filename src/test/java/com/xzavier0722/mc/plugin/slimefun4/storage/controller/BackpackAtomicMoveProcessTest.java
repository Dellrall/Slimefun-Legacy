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
class BackpackAtomicMoveProcessTest {
    @TempDir
    Path directory;

    enum Boundary {
        CLEAN_SHUTDOWN(0, true, false),
        BEFORE_FIRST_STATEMENT(81, false, false),
        AFTER_INSERT_BEFORE_COMMIT(82, false, false),
        AFTER_DELETE_BEFORE_COMMIT(83, false, true),
        BEFORE_COMMIT(84, false, false),
        AFTER_COMMIT_BEFORE_ACK(85, true, false),
        AFTER_ACK(86, true, false);

        final int exitCode;
        final boolean committed;
        final boolean deleteFirst;

        Boundary(int exitCode, boolean committed, boolean deleteFirst) {
            this.exitCode = exitCode;
            this.committed = committed;
            this.deleteFirst = deleteFirst;
        }
    }

    @ParameterizedTest
    @EnumSource(Boundary.class)
    void interruptedTwoSlotMovesConserveItemsAndPreserveUnrelatedRows(Boundary boundary) throws Exception {
        String nonce = UUID.randomUUID().toString();
        Set<Long> pids = new LinkedHashSet<>();
        pids.add(run("SEED", boundary, nonce, 0));
        pids.add(run("WRITE", boundary, nonce, boundary.exitCode));
        pids.add(run("VERIFY", boundary, nonce, 0));
        assertEquals(3, pids.size(), "Seeding, writing and verification must use distinct JVMs");
        System.out.println("ATOMIC_MOVE_PASSED " + boundary + " total=46 pids=" + pids);
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
                        BackpackAtomicMoveProcessProbe.class.getName(),
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
            String evidence = System.getenv("SFL_BACKPACK_EVIDENCE");
            if (evidence != null) {
                Path destination = Path.of(evidence, boundary.name(), nonce);
                Files.createDirectories(destination);
                Files.writeString(destination.resolve(phase + ".log"), output);
            }
            assertEquals(expectedExit, process.exitValue(), output);
            String marker = "BACKPACK_ATOMIC_MOVE:" + nonce + ":" + phase + ":" + process.pid();
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
        for (ClassLoader loader = BackpackAtomicMoveProcessTest.class.getClassLoader();
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
        entries.add(Path.of(BackpackAtomicMoveProcessProbe.class
                        .getProtectionDomain()
                        .getCodeSource()
                        .getLocation()
                        .toURI())
                .toString());
        return entries.stream().filter(entry -> !entry.isBlank()).collect(Collectors.joining(File.pathSeparator));
    }
}
