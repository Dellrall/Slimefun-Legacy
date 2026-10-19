#!/usr/bin/env python3
"""Offline compatibility contracts for the shared 26.2/Purpur/Folia-26.3 runtime smoke harness."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "paper_family_26_2_runtime_smoke.sh"


def probe(software: str, minecraft: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["SERVER_SOFTWARE"] = software
    env["SERVER_MINECRAFT_VERSION"] = minecraft
    env["SLIMEFUN_SMOKE_VERSION"] = next(
        row.split("=", 1)[1]
        for row in (ROOT / "gradle.properties").read_text(encoding="utf-8").splitlines()
        if row.startswith("projectVersion=")
    )
    # The fake JAR fails before any download or world creation is attempted.
    return subprocess.run(
        ["bash", str(SCRIPT), str(ROOT / "missing-purpur-milestone-test.jar")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


class TestPurpur263RuntimeContract(unittest.TestCase):
    def test_supported_existing_26_2_targets_unchanged(self) -> None:
        for software in ("purpur", "folia", "leaf"):
            with self.subTest(software=software):
                result = probe(software, "26.2")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Slimefun JAR not found or empty", result.stderr)
                self.assertNotIn("Unsupported server/version combination", result.stderr)

    def test_purpur_and_folia_26_3_are_explicit_candidates(self) -> None:
        for software in ("purpur", "folia"):
            with self.subTest(software=software):
                result = probe(software, "26.3")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Slimefun JAR not found or empty", result.stderr)
                self.assertNotIn("Unsupported server/version combination", result.stderr)

    def test_leaf_26_3_is_not_prematurely_claimed(self) -> None:
        result = probe("leaf", "26.3")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported server/version combination", result.stderr)

    def test_future_purpur_versions_are_not_implicitly_certified(self) -> None:
        result = probe("purpur", "26.4")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported server/version combination", result.stderr)

    def test_build_pin_is_validated_against_official_manifest(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("PURPUR_SMOKE_BUILD", source)
        self.assertIn("any(.builds.all[]?; tostring == $build)", source)
        self.assertIn("SERVER_BUILD=\"$PURPUR_SMOKE_BUILD\"", source)
        self.assertIn("${MC_VERSION} runtime smoke: PASS", source)

    def test_extra_addon_runtime_inputs_fail_closed_before_download(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_core = root / "core.jar"
            fake_core.write_bytes(b"not-a-real-jar-but-nonempty")
            expected = root / "expected-addons.txt"
            expected.write_text("Example.jar\tExampleAddon\n", encoding="utf-8")

            env = os.environ.copy()
            env["SERVER_SOFTWARE"] = "folia"
            env["SERVER_MINECRAFT_VERSION"] = "26.3"
            env["SLIMEFUN_SMOKE_VERSION"] = next(
                row.split("=", 1)[1]
                for row in (ROOT / "gradle.properties").read_text(encoding="utf-8").splitlines()
                if row.startswith("projectVersion=")
            )
            env["SLIMEFUN_SMOKE_EXTRA_PLUGIN_DIR"] = str(root / "missing-addons")
            env["SLIMEFUN_SMOKE_EXPECT_PLUGINS_FILE"] = str(expected)

            result = subprocess.run(
                ["bash", str(SCRIPT), str(fake_core), str(root / "work")],
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Extra plugin directory does not exist", result.stderr)
            self.assertFalse((root / "work" / "server.jar").exists())

    def test_extra_addon_runtime_requires_enable_lines_on_each_boot(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("SLIMEFUN_SMOKE_EXTRA_PLUGIN_DIR", source)
        self.assertIn("SLIMEFUN_SMOKE_EXPECT_PLUGINS_FILE", source)
        self.assertIn('grep -Fq "Enabling ${plugin} v"', source)
        self.assertIn("Declared Folia addons enabled per boot", source)


if __name__ == "__main__":
    unittest.main()
