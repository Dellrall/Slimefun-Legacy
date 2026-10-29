import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_maintained_sources as audit
from scripts.audit_maintained_sources import in_scope, exact_runs


class AuditScopeTest(unittest.TestCase):
    def repo(self, name="SF_Test", **changes):
        repo = {"name": name, "owner": {"login": "wickidcow"}, "private": False, "archived": False}
        repo.update(changes)
        return repo

    def test_only_explicit_public_maintained_scope(self):
        for name in ("SF_NetworksExp", "SF_FinalTECH", "Slimefun-Legacy", "WorldEditSlimefun"):
            self.assertTrue(in_scope(self.repo(name)))
        for name in ("pylon", "rebar", "AlbionMC-Control", "Rebar_VaultWorks", "SF_../escape", "OtherAddon"):
            self.assertFalse(in_scope(self.repo(name)))

    def test_archived_private_foreign_and_missing_metadata_are_rejected(self):
        self.assertFalse(in_scope(self.repo(archived=True)))
        self.assertFalse(in_scope(self.repo(private=True)))
        self.assertFalse(in_scope(self.repo(owner={"login": "other"})))
        self.assertFalse(in_scope({"name": "SF_Test"}))

    def test_historical_failure_does_not_override_current_head(self):
        rows = [{"id": 1, "workflow_id": 9, "head_sha": "old", "conclusion": "failure"},
                {"id": 2, "workflow_id": 9, "head_sha": "new", "conclusion": "success"}]
        self.assertEqual("success", exact_runs(rows, "new")[0]["conclusion"])
        self.assertEqual([], exact_runs(rows, "absent"))

    def test_latest_retry_and_event_are_kept_separate(self):
        rows = [{"id": 1, "workflow_id": 9, "head_sha": "same", "event": "push", "run_attempt": 1, "conclusion": "failure"},
                {"id": 1, "workflow_id": 9, "head_sha": "same", "event": "push", "run_attempt": 2, "conclusion": "success"},
                {"id": 2, "workflow_id": 9, "head_sha": "same", "event": "pull_request", "conclusion": None}]
        results = {r["event"]: r for r in exact_runs(rows, "same")}
        self.assertEqual("success", results["push"]["conclusion"])
        self.assertIsNone(results["pull_request"]["conclusion"])

    def test_green_follower_with_matching_default_sha_is_not_exact_source_evidence(self):
        # workflow_run metadata can name default HEAD while its artifacts were
        # built from the upstream PR. Matching head_sha alone cannot prove it.
        rows = [{"id": 1, "workflow_id": 9, "head_sha": "master", "event": "push", "conclusion": "success"},
                {"id": 2, "workflow_id": 10, "head_sha": "master", "event": "workflow_run", "conclusion": "success"}]
        before = copy.deepcopy(rows)
        self.assertEqual([1], [row["id"] for row in exact_runs(rows, "master")])
        self.assertEqual([], exact_runs(rows, "actual-pr-source"))
        self.assertEqual(before, rows)

    def test_follower_metadata_is_retained_separately_without_source_claim(self):
        rows = [{"id": 1, "workflow_id": 9, "head_sha": "master", "event": "push", "conclusion": "success"},
                {"id": 2, "workflow_id": 10, "head_sha": "master", "event": "workflow_run", "run_attempt": 1, "conclusion": "success"},
                {"id": 2, "workflow_id": 10, "head_sha": "master", "event": "workflow_run", "run_attempt": 2, "conclusion": "failure"}]
        before = copy.deepcopy(rows)
        candidates = audit.workflow_run_candidates(rows)
        self.assertEqual(1, len(candidates))
        candidate = candidates[0]
        self.assertEqual(2, candidate["id"])
        self.assertEqual(2, candidate["run_attempt"])
        self.assertEqual("failure", candidate["conclusion"])
        self.assertFalse(candidate["tested_source_verified"])
        self.assertIn("artifact", candidate["source_verification_required"])
        self.assertEqual(before, rows)

    def test_missing_runs_are_absent_evidence_not_success(self):
        self.assertEqual([], exact_runs([], "head"))
        self.assertEqual([], audit.workflow_run_candidates([]))

    def test_followers_of_different_workflows_are_not_combined(self):
        rows = [{"id": 2, "workflow_id": 10, "head_sha": "master", "event": "workflow_run", "conclusion": "success"},
                {"id": 3, "workflow_id": 11, "head_sha": "master", "event": "workflow_run", "conclusion": "failure"}]
        self.assertEqual([2, 3], [row["id"] for row in audit.workflow_run_candidates(rows)])
        self.assertEqual([], exact_runs(rows, "master"))

    def test_snapshot_classifies_default_and_pr_follower_metadata(self):
        sha, pr_sha, tree = "a" * 40, "b" * 40, "c" * 40
        run = {"id": 1, "workflow_id": 9, "event": "workflow_run", "conclusion": "success"}
        repo = self.repo(default_branch="master")
        prefix = "/repos/wickidcow/SF_Test"
        replies = {
            prefix + "/git/ref/heads/master": {"object": {"sha": sha}},
            prefix + "/git/commits/" + sha: {"tree": {"sha": tree}},
            prefix + f"/actions/runs?head_sha={sha}&per_page=100": {"total_count": 1, "workflow_runs": [dict(run, head_sha=sha)]},
            prefix + f"/actions/runs?head_sha={pr_sha}&per_page=100": {"total_count": 1, "workflow_runs": [dict(run, id=2, head_sha=pr_sha)]},
        }
        lists = {
            prefix + "/issues?state=open": [],
            prefix + "/pulls?state=open": [{"number": 3, "head": {"sha": pr_sha, "ref": "fix"},
                                             "base": {"sha": sha, "ref": "master"}}],
            prefix + "/pulls/3/files": [],
        }

        def fake_git(root, *args):
            if args == ("rev-parse", "HEAD"):
                return sha
            if args == ("rev-parse", "HEAD^{tree}"):
                return tree
            return ""

        with tempfile.TemporaryDirectory() as temp, patch.object(audit, "api", side_effect=replies.__getitem__), \
                patch.object(audit, "pages", side_effect=lists.__getitem__), patch.object(audit, "git", side_effect=fake_git):
            result = audit.snapshot(repo, Path(temp))
            self.assertEqual("complete", result["snapshot_status"])
            recorded = json.loads((Path(temp) / "SF_Test/inventory.json").read_text())
        self.assertEqual([], recorded["current_head_runs"])
        self.assertEqual([], recorded["pull_requests"][0]["runs"])
        self.assertEqual(1, recorded["workflow_run_candidates"][0]["id"])
        self.assertEqual(2, recorded["pull_requests"][0]["workflow_run_candidates"][0]["id"])
        self.assertFalse(recorded["workflow_run_candidates"][0]["tested_source_verified"])
        self.assertFalse(recorded["pull_requests"][0]["workflow_run_candidates"][0]["tested_source_verified"])
        self.assertFalse(recorded["source_matches_are_compiler_diagnostics"])
        self.assertTrue(recorded["read_only"])


if __name__ == "__main__":
    unittest.main()
