#!/usr/bin/env python3
"""Offline proof that Geyser companion release copying never modifies the ZIP."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_geyser_companion_release import (  # noqa: E402
    CarryForwardError, load_pin, plan, verify_after,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/carry-geyser-companion-release.yml"
PIN = load_pin()


def item(name, number, *, companion=False):
    return {
        "id": number,
        "name": name,
        "size": PIN["size_bytes"] if companion else 200,
        "digest": "sha256:" + (PIN["sha256"] if companion else "b" * 64),
        "state": "uploaded",
    }


def release(tag, identifier, *, with_companion=False):
    assets = [
        item("Slimefun-Legacy" + tag[1:] + ".jar", 1000),
        item("SF_Addons_1.21.11-26.3.zip", 1001),
        item("SlimefunLegacyRP.zip", 1002),
    ]
    if with_companion:
        number = PIN["source_asset_id"] if tag == PIN["source_release_tag"] else 50000000
        assets.append(item(PIN["asset_name"], number, companion=True))
    return {
        "id": identifier,
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "immutable": False,
        "assets": assets,
    }


def origin():
    return release("v4.1.77", PIN["source_release_id"], with_companion=True)


class CompanionPolicyTests(unittest.TestCase):
    def test_exact_v4177_source_is_already_present(self):
        state = origin()
        receipt = plan(state, state, PIN)
        self.assertEqual("verify", receipt["action"])
        self.assertEqual("PASS", verify_after(state, state, state, PIN)["result"])

    def test_future_release_adds_exactly_one_opaque_download(self):
        source = origin()
        before = release("v4.1.78", 421500001)
        self.assertEqual("upload", plan(source, before, PIN)["action"])
        after = copy.deepcopy(before)
        after["assets"].append(item(PIN["asset_name"], 99011, companion=True))
        result = verify_after(source, before, after, PIN)
        self.assertEqual("upload", result["action"])
        self.assertEqual(3, result["other_assets_preserved"])

    def test_covered_future_versions_and_idempotency(self):
        for tag in ("v4.1.78", "v4.1.99", "v4.2.0", "v5.0.0"):
            with self.subTest(tag=tag):
                existing = release(tag, 421500001, with_companion=True)
                self.assertEqual("verify", plan(origin(), existing, PIN)["action"])
                self.assertEqual("verify", verify_after(origin(), existing, existing, PIN)["action"])

    def test_rejects_unapproved_source_or_target_asset(self):
        scenarios = [
            ("source_id", lambda s, t: s["assets"][-1].update(id=123)),
            ("source_digest", lambda s, t: s["assets"][-1].update(digest="sha256:" + "0"*64)),
            ("source_size", lambda s, t: s["assets"][-1].update(size=123)),
            ("source_tag", lambda s, t: s.update(tag_name="v4.1.76")),
            ("source_release", lambda s, t: s.update(id=123)),
            ("target_tag_old", lambda s, t: t.update(tag_name="v4.1.76")),
            ("target_draft", lambda s, t: t.update(draft=True)),
            ("target_pending", lambda s, t: t["assets"][0].update(state="starter")),
            ("target_core_missing", lambda s, t: t["assets"].pop(0)),
            ("target_bundle_missing", lambda s, t: t["assets"].pop(1)),
            ("target_duplicate", lambda s, t: t["assets"].append(t["assets"][0])),
        ]
        for name, change in scenarios:
            with self.subTest(name=name):
                source, target = origin(), release("v4.1.78", 421500001)
                change(source, target)
                with self.assertRaises(CarryForwardError):
                    plan(source, target, PIN)

    def test_refuses_modified_or_replaced_future_companion(self):
        for key, value in (
            ("digest", "sha256:" + "0" * 64),
            ("size", 1),
            ("name", "OtherGeyser.zip"),
        ):
            with self.subTest(key=key):
                target = release("v4.1.78", 421500001, with_companion=True)
                target["assets"][-1][key] = value
                if key == "name":
                    # The approved companion must not be mistaken for a different asset.
                    # A separate unknown asset cannot satisfy release preservation.
                    self.assertEqual("upload", plan(origin(), target, PIN)["action"])
                else:
                    with self.assertRaises(CarryForwardError):
                        plan(origin(), target, PIN)

    def test_post_copy_checks_all_original_assets(self):
        source = origin()
        before = release("v4.1.78", 421500001)
        for mutation in ("missing", "replace", "digest", "extra"):
            with self.subTest(mutation=mutation):
                after = release("v4.1.78", 421500001, with_companion=True)
                if mutation == "missing":
                    after["assets"].pop(1)
                elif mutation == "replace":
                    after["assets"][0]["id"] = 2000
                elif mutation == "digest":
                    after["assets"][2]["digest"] = "sha256:" + "9"*64
                else:
                    after["assets"].append(item("new-extra.zip", 10099))
                with self.assertRaises(CarryForwardError):
                    verify_after(source, before, after, PIN)

    def test_source_pin_and_workflow_scope_are_exact(self):
        self.assertEqual("v4.1.77", PIN["source_release_tag"])
        self.assertEqual(421464301, PIN["source_release_id"])
        self.assertEqual(669444618, PIN["source_asset_id"])
        self.assertEqual(1339867, PIN["size_bytes"])
        self.assertEqual("e11e5f8e6ede75a17421039e50178e83e11e9cf7f020e99596cfc078801b8c58",
                         PIN["sha256"])
        wf = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflows: ['Reproducible Release']", wf)
        self.assertIn("types: [completed]", wf)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", wf)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository", wf)
        self.assertIn("github.event_name != 'pull_request'", wf)
        self.assertIn("gh release upload \"$TARGET_TAG\"", wf)
        self.assertNotIn("--clobber", wf)
        self.assertIn("sha256sum -c", wf)
        self.assertIn("scripts/verify_geyser_companion_release.py verify", wf)
        self.assertIn("Geyser installs and manages this companion", wf)
        self.assertNotIn("mcpack", wf.lower())
        self.assertNotIn("custom_mappings", wf)


if __name__ == "__main__":
    unittest.main(verbosity=2)
