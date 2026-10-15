"""Offline release-admission contracts; these never publish or run a server."""
import copy
import io
import unittest
import zipfile
import xml.etree.ElementTree as ET

from prepare_r137_release_candidate import (inspect_unit_reports, validate_artifact,
                                            validate_release, validate_source_run)


class CandidateContracts(unittest.TestCase):
    def setUp(self):
        self.config = {"release_id": 123, "core_source_commit": "c" * 40,
                       "source_run_id": 456, "new_commit": "d" * 40,
                       "baseline_assets": {"bundle.zip": {"id": 7, "size": 20, "sha256": "a" * 64},
                                           "core.jar": {"id": 8, "size": 30, "sha256": "b" * 64}}}
        self.release = {"id": 123, "tag_name": "v4.1.74", "target_commitish": "c" * 40,
                        "draft": False, "prerelease": False, "assets": [
                            {"name": name, **row, "digest": "sha256:" + row["sha256"], "state": "uploaded"}
                            for name, row in self.config["baseline_assets"].items()]}
        self.run = {"id": 456, "head_sha": "d" * 40, "status": "completed", "conclusion": "success",
                    "path": ".github/workflows/build.yml", "event": "pull_request",
                    "repository": {"full_name": "wickidcow/SF_MagicExpansion"}}
        self.expected = {"id": 99, "sha256": "e" * 64}
        self.artifact = {"id": 99, "name": "raw.jar", "expired": False, "digest": "sha256:" + "e" * 64,
                         "workflow_run": {"id": 456, "head_sha": "d" * 40}}

    def reports(self, change=None):
        suites = []
        for i, count in enumerate([40] + [8] * 12 + [10]):
            suite = ET.Element("testsuite", name="BlackMarketTest" if i == 0 else f"General{i}",
                               tests=str(count), failures="0", errors="0", skipped="0")
            for case in range(count):
                ET.SubElement(suite, "testcase", name=f"test{case}")
            suites.append(suite)
        if change:
            change(suites)
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            for i, suite in enumerate(suites):
                archive.writestr(f"TEST-{i}.xml", ET.tostring(suite))
        return data.getvalue()

    def test_exact_release_admitted_without_mutation(self):
        before = copy.deepcopy(self.release)
        validate_release(self.release, self.config)
        self.assertEqual(self.release, before)

    def test_changed_release_identity_refused(self):
        for key, value in (("id", 124), ("tag_name", "v4.1.75"), ("target_commitish", "f" * 40),
                           ("draft", True), ("prerelease", True)):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.release); changed[key] = value
                with self.assertRaises(ValueError): validate_release(changed, self.config)

    def test_changed_asset_lease_refused(self):
        for key, value in (("id", 100), ("size", 999), ("digest", "sha256:" + "f" * 64), ("state", "new")):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.release); changed["assets"][0][key] = value
                with self.assertRaises(ValueError): validate_release(changed, self.config)

    def test_added_removed_or_duplicate_assets_refused(self):
        variants = [self.release["assets"][:-1], self.release["assets"] + [self.release["assets"][0]],
                    [self.release["assets"][0], self.release["assets"][0]]]
        for rows in variants:
            changed = copy.deepcopy(self.release); changed["assets"] = rows
            with self.assertRaises(ValueError): validate_release(changed, self.config)

    def test_exact_source_run_admitted(self):
        validate_source_run(self.run, self.config)

    def test_wrong_or_incomplete_source_run_refused(self):
        for key, value in (("id", 457), ("head_sha", "f" * 40), ("conclusion", "failure"),
                           ("status", "in_progress"), ("event", "workflow_dispatch"),
                           ("path", ".github/workflows/unrelated.yml"),
                           ("repository", {"full_name": "other/repo"})):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.run); changed[key] = value
                with self.assertRaises(ValueError): validate_source_run(changed, self.config)

    def test_exact_artifact_admitted(self):
        validate_artifact(self.artifact, self.config, "raw.jar", self.expected)

    def test_wrong_expired_or_changed_artifact_refused(self):
        for key, value in (("id", 100), ("name", "other.jar"), ("expired", True),
                           ("digest", "sha256:" + "f" * 64),
                           ("workflow_run", {"id": 456, "head_sha": "f" * 40})):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.artifact); changed[key] = value
                with self.assertRaises(ValueError): validate_artifact(changed, self.config, "raw.jar", self.expected)

    def test_exact_146_executed_cases_admitted(self):
        counts = inspect_unit_reports(self.reports())
        self.assertEqual((counts["tests"], counts["suites"], counts["black_market_tests"]), (146, 14, 40))

    def test_inflated_counts_without_executed_cases_refused(self):
        with self.assertRaises(ValueError):
            inspect_unit_reports(self.reports(lambda suites: suites[1].remove(suites[1][0])))

    def test_failed_or_skipped_cases_refused_even_if_summary_claims_zero(self):
        for tag in ("failure", "error", "skipped"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                inspect_unit_reports(self.reports(lambda suites: ET.SubElement(suites[1][0], tag)))

    def test_missing_black_market_coverage_refused(self):
        with self.assertRaises(ValueError):
            inspect_unit_reports(self.reports(lambda suites: suites[0].set("name", "UnrelatedTest")))


if __name__ == "__main__":
    unittest.main()
