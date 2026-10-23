#!/usr/bin/env python3
"""Offline tests: Geyser archive is copied unchanged, never opened."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from carry_forward_geyser_release_asset import CarryError, GEYSER_ASSET, select, verify_file, verify_published

PAYLOAD = b"Opaque Geyser pack test bytes; no Minecraft content inspection"


def sample(tag="v4.1.76", *, data=PAYLOAD, present=True):
    return {"tag_name": tag, "draft": False, "prerelease": False,
            "assets": [{"id": 8, "name": GEYSER_ASSET, "state": "uploaded",
                        "size": len(data), "digest": "sha256:" + hashlib.sha256(data).hexdigest()}]
            if present else []}


class GeyserCarryForwardTests(unittest.TestCase):
    def setUp(self):
        self.selection = select([sample(), sample("v4.1.75", present=False)], "v4.1.77")

    def test_next_version_carries_latest_prior_release(self):
        self.assertEqual("v4.1.76", self.selection["source_tag"])
        self.assertEqual("v4.1.77", self.selection["target_tag"])
        self.assertEqual(GEYSER_ASSET, self.selection["asset_name"])
        self.assertEqual(hashlib.sha256(PAYLOAD).hexdigest(), self.selection["sha256"])

    def test_existing_release_can_validate_its_own_pack(self):
        self.assertEqual("v4.1.76", select([sample()], "v4.1.76")["source_tag"])

    def test_newer_pack_preferred_but_never_copied_backward(self):
        future = sample("v4.1.78", data=b"future")
        self.assertEqual("v4.1.76", select([future, sample()], "v4.1.77")["source_tag"])
        newer = sample("v4.1.77", data=b"new independently published ZIP")
        self.assertEqual("v4.1.77", select([sample(), newer], "v4.1.78")["source_tag"])

    def test_missing_duplicate_undigested_and_incomplete_assets_rejected(self):
        standard = sample()["assets"][0]
        states = [
            [sample(present=False)],
            [sample(data=b"")],
            [sample() | {"assets": [standard, standard]}],
            [sample() | {"assets": [standard | {"digest": "invalid"}]}],
            [sample() | {"assets": [standard | {"state": "processing"}]}],
            [sample() | {"assets": [standard | {"name": "unrelated.zip"}]}],
        ]
        for releases in states:
            with self.subTest(releases=releases), self.assertRaises(CarryError):
                select(releases, "v4.1.77")

    def test_file_sha_size_filename_and_future_source_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / GEYSER_ASSET
            original.write_bytes(PAYLOAD)
            self.assertTrue(verify_file(self.selection, original)["bytes_carried_unchanged"])
            original.write_bytes(b"altered")
            with self.assertRaises(CarryError):
                verify_file(self.selection, original)
            original.write_bytes(PAYLOAD)
            wrong_name = Path(tmp) / "elsewhere.zip"
            wrong_name.write_bytes(PAYLOAD)
            with self.assertRaises(CarryError):
                verify_file(self.selection, wrong_name)
            with self.assertRaises(CarryError):
                verify_file(dict(self.selection, source_tag="v4.1.78"), original)

    def test_published_digest_and_size_must_match_source(self):
        self.assertTrue(verify_published(self.selection, sample("v4.1.77"))["published_unchanged"])
        for updates in ({"digest": "sha256:" + "0" * 64}, {"size": 999},
                        {"state": "processing"}):
            target = sample("v4.1.77")
            target["assets"][0].update(updates)
            with self.subTest(updates=updates), self.assertRaises(CarryError):
                verify_published(self.selection, target)

    def test_release_tags_are_stable(self):
        for tag in ("4.1.77", "v4.1.77-rc1", "v4.1.77\n"):
            with self.subTest(tag=tag), self.assertRaises(CarryError):
                select([sample()], tag)


class ReleaseWorkflowPolicyTests(unittest.TestCase):
    def test_release_workflow_uses_opaque_geyser_copy_not_mappings(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/reproducible-release.yml").read_text()
        self.assertIn("Carry forward latest published Geyser ZIP unchanged", workflow)
        self.assertIn("carry_forward_geyser_release_asset.py select", workflow)
        self.assertIn("carry_forward_geyser_release_asset.py verify", workflow)
        self.assertIn("carry_forward_geyser_release_asset.py verify-published", workflow)
        self.assertIn("cmp ", workflow)
        self.assertNotIn("python3 scripts/verify_release_bedrock_pack.py", workflow)
        self.assertNotIn("SFL_GEYSER_RP_experimental_v1.0.3_complete.zip", workflow)
        self.assertIn("OPTIONAL_GEYSER_PACK: " + GEYSER_ASSET, workflow)
        self.assertIn("CANONICAL_ADDON_BUNDLE: SF_Addons_1.21.11-26.3.zip", workflow)


if __name__ == "__main__":
    # verify_legacy.py passes the repository root as a positional argument.
    unittest.main(argv=[sys.argv[0]])
