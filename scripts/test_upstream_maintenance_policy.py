#!/usr/bin/env python3
"""Exercise the live polling and CI target selection without querying remote forks."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import check_upstream_candidates as radar


ROOT = Path(__file__).resolve().parents[1]


class UpstreamMaintenancePolicyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.manifest = radar.load_manifest(ROOT / "compatibility/upstream-sources.json")
        self.matrix = json.loads((ROOT / "compatibility/cross-fork-api-matrix.json").read_text())

    def write(self, name, data):
        path = self.directory / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def generate(self, data):
        matrix = self.write("matrix.json", data)
        output = self.directory / "github-output"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_cross_fork_api_matrix.py"),
             str(matrix), "--github-output", str(output)],
            capture_output=True, text=True, check=False,
        )
        return result, output

    def test_online_radar_queries_only_gugu_and_leaves_historical_references_unqueried(self):
        self.assertTrue(self.manifest["historical_references"])
        reviewed = self.manifest["sources"][0]["reviewed_commit"]
        with patch.object(radar, "github_head", return_value=reviewed) as query:
            results = radar.check_sources(self.manifest, offline=False)
        self.assertEqual(1, query.call_count)
        self.assertEqual(("SlimefunGuguProject/Slimefun4", "master"), query.call_args.args[:2])
        self.assertEqual([("slimefun-gugu", "CURRENT")], [(row.source_id, row.status) for row in results])

    def test_offline_radar_never_queries_a_repository(self):
        with patch.object(radar, "github_head", side_effect=AssertionError("Unexpected remote query")):
            results = radar.check_sources(self.manifest, offline=True)
        self.assertEqual([("slimefun-gugu", "OFFLINE")], [(row.source_id, row.status) for row in results])

    def test_radar_rejects_reintroducing_a_retired_source(self):
        for source_id in ("slimefun-original", "slimefun-united", "slimefun5", "slimefun4core"):
            with self.subTest(source_id=source_id):
                manifest = copy.deepcopy(self.manifest)
                extra = copy.deepcopy(manifest["sources"][0])
                extra["id"] = source_id
                manifest["sources"].append(extra)
                with self.assertRaisesRegex(ValueError, "Only GuGu may be polled"):
                    radar.load_manifest(self.write("sources.json", manifest))

    def test_radar_rejects_repository_substitution_under_gugu_identifier(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["sources"][0]["repository"] = "Slimefun-United/Slimefun-United"
        with self.assertRaisesRegex(ValueError, "Only GuGu may be polled"):
            radar.load_manifest(self.write("sources.json", manifest))

    def test_generated_ci_matrix_contains_only_the_maintained_gugu_repository(self):
        result, output = self.generate(self.matrix)
        self.assertEqual(0, result.returncode, result.stderr)
        rows = json.loads(result.stdout)["include"]
        self.assertEqual([("gugu", "SlimefunGuguProject/Slimefun4", True)],
                         [(row["id"], row["repository"], row["advisory"]) for row in rows])
        self.assertIn("enabled_count=1\n", output.read_text())

    def test_ci_generation_rejects_retired_targets_before_writing_jobs(self):
        matrix = copy.deepcopy(self.matrix)
        retired = copy.deepcopy(matrix["cores"][0])
        retired.update(id="united", repository="Slimefun-United/Slimefun-United")
        matrix["cores"].append(retired)
        result, output = self.generate(matrix)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Only GuGu is an active", result.stderr)
        self.assertFalse(output.exists())

    def test_missing_maintenance_policy_fails_closed(self):
        manifest = copy.deepcopy(self.manifest)
        del manifest["policy"]["active_upstream_ids"]
        with self.assertRaisesRegex(ValueError, "must select GuGu only"):
            radar.load_manifest(self.write("sources.json", manifest))
        matrix = copy.deepcopy(self.matrix)
        del matrix["policy"]["active_upstream_core_variants"]
        result, output = self.generate(matrix)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("must select GuGu only", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(argv=[__file__])
