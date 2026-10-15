"""Offline setup-contract tests. Fake JAR bytes and mocked javac are not runtime evidence."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SOURCE = Path(__file__).resolve().parent / "runtime/r135_fluffy_networks/run_probe.py"
SPEC = importlib.util.spec_from_file_location("native_storage_probe", SOURCE)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class NativeStorageProbeContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.work = self.root / "build/full-stack-26.3"
        self.plugins = self.work / "plugins"
        self.plugins.mkdir(parents=True)
        for name, data in {
            "smoke-result.txt": "runtime smoke: PASS\n",
            "server.jar": "synthetic server bytes",
            "eula.txt": "eula=true\n",
            "server.properties": "online-mode=false\nserver-ip=127.0.0.1\n",
        }.items():
            (self.work / name).write_text(data, encoding="utf-8")
        (self.plugins / "Slimefun-Legacy-full-stack.jar").write_bytes(b"synthetic core")
        self.java = self.root / "jdk/bin/java"
        self.java.parent.mkdir(parents=True)
        self.java.write_text("not executable", encoding="utf-8")
        self.java.with_name("javac").write_text("not executable", encoding="utf-8")
        self.sources = self.root / "synthetic-probe-source"
        self.sources.mkdir()
        (self.sources / "plugin.yml").write_text("name: SyntheticContractOnly\n", encoding="utf-8")
        self.bundle = self.root / "bundle.zip"
        self.manifest = {"bundle_revision": 138, "addons": []}
        self.populate(138)
        self.addCleanup(patch.stopall)
        patch.object(probe.Path, "cwd", return_value=self.root).start()
        patch.object(probe, "HERE", self.sources).start()
        self.compile = patch.object(
            probe.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0, "", ""),
        ).start()
        self.launch = patch.object(
            probe.subprocess, "Popen", side_effect=AssertionError("No server may run in offline contract tests")
        ).start()

    def populate(self, revision):
        self.manifest["bundle_revision"] = revision
        expected = dict(probe.EXPECTED_VERSIONS)
        expected["wickidcow/SF_NetworksExp"] = (
            ("SF_Networks1.0.54.jar", "c24064cbeafe4f112c7d46bf3de5617fa151d88d")
            if revision == 135 else
            ("SF_Networks1.0.55.jar", "bcdef34d362dc74aa1aab23c8961a629daa79950")
        )
        rows = []
        for repository, (filename, commit) in expected.items():
            binary = self.plugins / filename
            binary.write_bytes(("synthetic JAR: " + repository).encode("utf-8"))
            rows.append({"repository": repository, "jar": filename,
                         "commit": commit, "sha256": probe.sha256(binary)})
        self.manifest["addons"] = rows

    def prepare(self, work=None):
        with zipfile.ZipFile(self.bundle, "w") as archive:
            archive.writestr("SF_ADDON_MANIFEST.json", json.dumps(self.manifest))
        return probe.prepare(work or self.work, self.bundle, self.java)

    def reject(self, message):
        with self.assertRaisesRegex(RuntimeError, message):
            self.prepare()
        self.compile.assert_not_called()
        self.launch.assert_not_called()

    def test_r138_reaches_native_setup_with_unchanged_exact_storage_pins(self):
        evidence = self.prepare()
        self.assertEqual(evidence["bundle_revision"], 138)
        self.assertEqual(evidence["status"], "STARTED")
        self.assertNotIn("result", evidence)  # Setup success must not claim a native PASS.
        networks = evidence["tested_addons"]["wickidcow/SF_NetworksExp"]
        self.assertEqual(networks["commit"], "bcdef34d362dc74aa1aab23c8961a629daa79950")
        self.assertEqual(networks["jar"], "SF_Networks1.0.55.jar")
        self.compile.assert_called_once()
        self.launch.assert_not_called()

    def test_r135_is_still_supported(self):
        self.populate(135)
        evidence = self.prepare()
        self.assertEqual(evidence["tested_addons"]["wickidcow/SF_NetworksExp"]["jar"], "SF_Networks1.0.54.jar")

    def test_r136_is_still_supported(self):
        self.populate(136)
        self.assertEqual(self.prepare()["bundle_revision"], 136)

    def test_r137_is_still_supported(self):
        self.populate(137)
        self.assertEqual(self.prepare()["bundle_revision"], 137)

    def test_unknown_revision_is_rejected_instead_of_skipped(self):
        self.manifest["bundle_revision"] = 139
        self.reject("requires r135, r136, r137 or r138")

    def test_non_integer_revisions_are_rejected(self):
        for value in (138.0, "138", True, None):
            with self.subTest(value=value):
                self.manifest["bundle_revision"] = value
                self.reject("requires r135, r136, r137 or r138")

    def test_wrong_networks_pin_is_rejected(self):
        self.manifest["addons"][1]["commit"] = "0" * 40
        self.reject("addon source mismatch")

    def test_wrong_fluffy_pin_is_rejected(self):
        self.manifest["addons"][0]["commit"] = "0" * 40
        self.reject("addon source mismatch")

    def test_wrong_jar_name_is_rejected(self):
        self.manifest["addons"][1]["jar"] = "SF_Networks1.0.54.jar"
        self.reject("addon source mismatch")

    def test_missing_required_addon_is_rejected(self):
        self.manifest["addons"].pop()
        self.reject("addon source mismatch")

    def test_altered_jar_bytes_are_rejected(self):
        (self.plugins / self.manifest["addons"][1]["jar"]).write_bytes(b"changed")
        self.reject("digest mismatch")

    def test_missing_jar_is_rejected(self):
        (self.plugins / self.manifest["addons"][1]["jar"]).unlink()
        self.reject("digest mismatch")

    def test_missing_digest_is_rejected(self):
        del self.manifest["addons"][1]["sha256"]
        self.reject("digest mismatch")

    def test_failed_double_boot_is_rejected(self):
        (self.work / "smoke-result.txt").write_text("runtime smoke: FAIL\n", encoding="utf-8")
        self.reject("baseline did not pass")

    def test_production_style_path_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "outside a disposable"):
            self.prepare(self.root / "production-server")
        self.compile.assert_not_called()

    def test_stale_probe_jar_is_rejected(self):
        (self.plugins / "R135FluffyNetworksProbe.jar").write_bytes(b"stale")
        self.reject("overwrite a prior")

    def test_compile_failure_is_not_a_success_or_skip(self):
        self.compile.return_value = subprocess.CompletedProcess([], 1, "", "synthetic compile failure")
        with self.assertRaisesRegex(RuntimeError, "did not compile"):
            self.prepare()
        self.assertFalse((self.plugins / "R135FluffyNetworksProbe.jar").exists())
        self.launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
