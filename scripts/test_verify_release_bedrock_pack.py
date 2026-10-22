#!/usr/bin/env python3
"""Offline identity/substitution and drop-in archive regressions for the Bedrock asset."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

import verify_release_bedrock_pack as subject

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_release_bedrock_pack.py"


def archive_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    stream = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in entries:
                archive.writestr(name, data)
    return stream.getvalue()


class BedrockAssetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.pin = subject.load_pin(ROOT / "compatibility/bedrock-resource-pack-release.json")
        self.manifest = {"format_version": 2, "header": {"name": "fixture"},
                         "modules": [{"type": "resources"}]}
        self.pack_entries = [
            ("SFB-RP/manifest.json", json.dumps(self.manifest).encode()),
            ("SFB-RP/textures/items/example.png", b"fixture-pixel"),
        ]
        mapping = json.dumps({"format_version": "1", "items": {"minecraft:stone": [{"name": "example"}]}}).encode()
        self.entries = [(f"{subject.MAPPINGS}mapping-{index}.json", mapping) for index in range(20)]
        self.entries.append((subject.MCPACK, archive_bytes(self.pack_entries)))

    def json_path(self, name, value):
        path = self.directory / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def source(self):
        return {
            "id": self.pin["release_id"], "tag_name": self.pin["release_tag"],
            "draft": False, "prerelease": False,
            "assets": [{"id": self.pin["asset_id"], "name": self.pin["asset_name"],
                        "state": "uploaded", "size": self.pin["size_bytes"],
                        "digest": "sha256:" + self.pin["sha256"]}],
        }

    def zip_fixture(self, entries=None):
        # Synthetic fixtures have their own explicit pin; production bytes never change.
        data = archive_bytes(self.entries if entries is None else entries)
        path = self.directory / "fixture.zip"
        path.write_bytes(data)
        pin = copy.deepcopy(self.pin)
        pin.update(size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        return path, pin

    def verify_entries(self, entries):
        path, pin = self.zip_fixture(entries)
        return subject.verify_zip(path, pin)

    def pack_outer(self, pack_entries):
        return [entry for entry in self.entries if entry[0] != subject.MCPACK] + [
            (subject.MCPACK, archive_bytes(pack_entries))]

    def test_pin_has_reviewed_origin_and_only_approved_successor(self):
        self.assertEqual("v4.1.75", self.pin["release_tag"])
        self.assertEqual(["v4.1.76"], self.pin["carry_forward_tags"])
        self.assertEqual(664136278, self.pin["asset_id"])
        self.assertEqual(226576, self.pin["size_bytes"])

    def test_pin_rejects_invalid_types_and_broad_targets(self):
        cases = {"schema_version": True, "repository": "other/repository", "release_tag": "latest",
                 "asset_name": "unreviewed.zip", "release_id": True, "asset_id": 0,
                 "size_bytes": "226576", "sha256": "invalid", "carry_forward_tags": ["*"],
                 "stability": "stable"}
        for key, value in cases.items():
            with self.subTest(key=key):
                pin = copy.deepcopy(self.pin)
                pin[key] = value
                with self.assertRaises(ValueError):
                    subject.load_pin(self.json_path("pin.json", pin))

    def test_pin_rejects_duplicate_or_source_target(self):
        for tags in ([], ["v4.1.76", "v4.1.76"], ["v4.1.75"], None):
            with self.subTest(tags=tags):
                pin = dict(self.pin, carry_forward_tags=tags)
                with self.assertRaises(ValueError):
                    subject.load_pin(self.json_path("pin.json", pin))

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            subject.json_data('{"asset_id": 1, "asset_id": 2}')

    def test_exact_source_release_is_accepted(self):
        subject.verify_source_release(self.json_path("source.json", self.source()), self.pin)

    def test_source_identity_tag_and_published_state_are_required(self):
        for key, value in (("id", 999), ("tag_name", "v4.1.74"), ("draft", True),
                           ("prerelease", True), ("draft", None)):
            with self.subTest(key=key, value=value):
                release = self.source()
                release[key] = value
                with self.assertRaises(ValueError):
                    subject.verify_source_release(self.json_path("source.json", release), self.pin)

    def test_source_asset_replacement_or_partial_upload_is_rejected(self):
        cases = (("id", 999), ("name", "different.zip"), ("size", 1), ("size", True),
                 ("digest", "sha256:" + "0" * 64), ("state", "starter"))
        for key, value in cases:
            with self.subTest(key=key):
                release = self.source()
                release["assets"][0][key] = value
                with self.assertRaises(ValueError):
                    subject.verify_source_release(self.json_path("source.json", release), self.pin)

    def test_duplicate_release_names_or_ids_are_rejected(self):
        for change in ({}, {"id": 987}, {"name": "different.zip"}):
            with self.subTest(change=change):
                release = self.source()
                release["assets"].append(dict(release["assets"][0], **change))
                with self.assertRaisesRegex(ValueError, "Duplicate release"):
                    subject.verify_source_release(self.json_path("source.json", release), self.pin)

    def test_target_allows_new_ids_only_for_approved_tag_and_identical_bytes(self):
        release = self.source()
        release.update(id=987, tag_name="v4.1.76")
        release["assets"][0]["id"] = 988
        path = self.json_path("target.json", release)
        subject.verify_target_release(path, "v4.1.76", self.pin)
        for tag in ("v4.1.75", "v4.1.77", "latest"):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "not approved"):
                subject.verify_target_release(path, tag, self.pin)

    def test_substituted_or_missing_target_asset_is_rejected(self):
        for change in ({"digest": "sha256:" + "f" * 64}, {"size": 1}, {"state": "starter"},
                       {"name": "Geyser-Spigot-RP-alpha-v0.0.3.zip"}):
            with self.subTest(change=change):
                release = self.source()
                release.update(id=987, tag_name="v4.1.76")
                release["assets"][0].update(change)
                with self.assertRaises(ValueError):
                    subject.verify_target_release(self.json_path("target.json", release), "v4.1.76", self.pin)

    def test_exact_fixture_with_enclosing_pack_directory_passes(self):
        report = self.verify_entries(self.entries)
        self.assertEqual({"mapping_files": 20, "pack_files": 2}, report)

    def test_root_pack_manifest_is_also_supported(self):
        entries = [(name.removeprefix("SFB-RP/"), data) for name, data in self.pack_entries]
        self.verify_entries(self.pack_outer(entries))

    def test_outer_size_and_digest_are_both_required(self):
        path, pin = self.zip_fixture()
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            subject.verify_zip(path, dict(pin, size_bytes=pin["size_bytes"] + 1))
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            subject.verify_zip(path, dict(pin, sha256="f" * 64))

    def test_missing_mapping_or_mcpack_is_rejected(self):
        for missing in (self.entries[0][0], subject.MCPACK):
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                self.verify_entries([entry for entry in self.entries if entry[0] != missing])

    def test_extra_drop_in_files_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected files"):
            self.verify_entries(self.entries + [("Geyser-Spigot/config.yml", b"unapproved")])

    def test_invalid_or_empty_custom_mapping_is_rejected(self):
        for data in (b"not json", b'{"format_version":"1","items":{}}',
                     b'{"format_version":"2","items":{"minecraft:stone":[]}}',
                     b'{"format_version":"1","items":{},"items":{"minecraft:stone":[]}}'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.verify_entries([(self.entries[0][0], data)] + self.entries[1:])

    def test_duplicate_outer_or_inner_entries_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate ZIP"):
            self.verify_entries(self.entries + [self.entries[0]])
        with self.assertRaisesRegex(ValueError, "Duplicate ZIP"):
            self.verify_entries(self.pack_outer(self.pack_entries + [self.pack_entries[0]]))

    def test_unsafe_outer_and_inner_paths_are_rejected(self):
        for name in ("../outside", "/absolute", "C:/drive", "a\\b", "a/./b", "a//b"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "Unsafe ZIP"):
                    self.verify_entries(self.entries + [(name, b"unsafe")])
                with self.assertRaisesRegex(ValueError, "Unsafe ZIP"):
                    self.verify_entries(self.pack_outer(self.pack_entries + [(name, b"unsafe")]))

    def test_inner_crc_failure_is_rejected(self):
        # Keep the same byte count so failure is CRC rather than ZIP offsets.
        pack = archive_bytes(self.pack_entries).replace(b"fixture-pixel", b"fixture-false", 1)
        entries = [entry for entry in self.entries if entry[0] != subject.MCPACK] + [(subject.MCPACK, pack)]
        with self.assertRaisesRegex(ValueError, "CRC"):
            self.verify_entries(entries)

    def test_outer_crc_failure_is_rejected(self):
        path, pin = self.zip_fixture()
        data = path.read_bytes().replace(b"minecraft:stone", b"minecraft:dirt_", 1)
        path.write_bytes(data)
        pin["sha256"] = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(ValueError, "CRC"):
            subject.verify_zip(path, pin)

    def test_missing_manifest_resource_module_or_textures_is_rejected(self):
        cases = [self.pack_entries[1:], self.pack_entries[:1],
                 [("SFB-RP/manifest.json", json.dumps(dict(self.manifest, modules=[])).encode()), self.pack_entries[1]]]
        for entries in cases:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                self.verify_entries(self.pack_outer(entries))

    def test_cli_checks_approved_target_before_publication_without_metadata(self):
        pin_path = self.json_path("pin.json", self.pin)
        for tag, expected in (("v4.1.76", 0), ("v4.1.77", 1)):
            with self.subTest(tag=tag):
                result = subprocess.run([sys.executable, str(SCRIPT), str(ROOT), "--pin", str(pin_path),
                                         "--target-tag", tag], capture_output=True, text=True, check=False)
                self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
                if expected:
                    self.assertIn("target release tag is not approved", result.stderr)
                    self.assertNotIn("verification passed", result.stdout)
                else:
                    self.assertIn("verification passed", result.stdout)

    def test_cli_accepts_all_checks_and_target_metadata_requires_tag(self):
        path, pin = self.zip_fixture()
        pin_path = self.json_path("pin.json", pin)
        release = self.source()
        release["assets"][0].update(size=pin["size_bytes"], digest="sha256:" + pin["sha256"])
        source_path = self.json_path("source.json", release)
        target = copy.deepcopy(release)
        target.update(id=987, tag_name="v4.1.76")
        target["assets"][0]["id"] = 988
        target_path = self.json_path("target.json", target)
        command = [sys.executable, str(SCRIPT), str(ROOT), "--pin", str(pin_path), "--release-json", str(source_path),
                   "--zip", str(path), "--target-release-json", str(target_path), "--target-tag", "v4.1.76"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("verification passed", result.stdout)
        result = subprocess.run(command[:-2], capture_output=True, text=True, check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("requires --target-tag", result.stderr)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
