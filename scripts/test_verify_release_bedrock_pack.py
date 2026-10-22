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
PYTHON = [sys.executable] + (["-O"] if sys.flags.optimize else [])


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
        self.valhalla_pack_entries = [
            ("manifest.json", json.dumps(self.manifest).encode()),
            ("textures/items/example.png", b"fixture-pixel"),
        ]
        self.stat_pack_entries = [
            ("manifest.json", json.dumps(self.manifest).encode()),
            ("pack_icon.png", b"fixture-pixel"),
            ("font/glyph_ED.png", b"fixture-pixel"),
            ("font/glyph_EE.png", b"fixture-pixel"),
        ]
        self.valhalla = {
            "format_version": 2,
            "items": {"minecraft:stone": [{
                "type": "definition", "model": "minecraft:stone", "bedrock_identifier": "albion_valhalla:example",
                "predicate": [{"type": "range_dispatch", "property": "custom_model_data",
                               "threshold": 1.0, "scale": 1.0, "index": 0}],
                "bedrock_options": {"icon": "albion_valhalla_example"},
            }]},
        }
        self.skulls = {"format_version": 1, "skulls": {
            "username": [], "uuid": [], "profile": [], "skin_hash": ["abc123", "1" * 64],
        }}
        self.new_skulls = copy.deepcopy(self.skulls)
        self.new_skulls["skulls"]["skin_hash"] = ["2" * 64]
        mapping = json.dumps({"format_version": "1", "items": {"minecraft:stone": [{"name": "example"}]}}).encode()
        self.entries = [(subject.MAPPINGS + name, mapping) for name in subject.BASE_MAPPING_NAMES]
        self.entries.extend([
            (subject.VALHALLA_MAPPING, json.dumps(self.valhalla).encode()),
            (subject.SKULL_MAPPING, json.dumps(self.skulls).encode()),
            (subject.NEW_SKULL_MAPPING, json.dumps(self.new_skulls).encode()),
            (subject.MCPACK, archive_bytes(self.pack_entries)),
            (subject.VALHALLA_PACK, archive_bytes(self.valhalla_pack_entries)),
            (subject.STAT_ICONS_PACK, archive_bytes(self.stat_pack_entries)),
            ("README.txt", b"Original overlay instructions. Base files must also be installed.\n"),
            ("INSTALL.md", b"Complete candidate: install packs and custom_mappings with Geyser.\n"),
        ])

    def json_path(self, name, value):
        path = self.directory / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def source(self, index=1):
        source = self.pin["source_assets"][index]
        return {
            "id": source["release_id"], "tag_name": source["release_tag"],
            "draft": False, "prerelease": False,
            "assets": [{"id": source["asset_id"], "name": source["asset_name"],
                        "state": "uploaded", "size": source["size_bytes"],
                        "digest": "sha256:" + source["sha256"]}],
        }

    def target(self, pin=None):
        candidate = self.pin if pin is None else pin
        return {
            "id": 987, "tag_name": "v4.1.76", "draft": False, "prerelease": False,
            "assets": [{"id": 988, "name": candidate["asset_name"], "state": "uploaded",
                        "size": candidate["size_bytes"], "digest": "sha256:" + candidate["sha256"]}],
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

    def replace_entry(self, name, data):
        return [(entry_name, data if entry_name == name else entry_data) for entry_name, entry_data in self.entries]

    def pack_outer(self, pack_entries, name=subject.MCPACK):
        return self.replace_entry(name, archive_bytes(pack_entries))

    def verify_mapping(self, name, mapping):
        return self.verify_entries(self.replace_entry(name, json.dumps(mapping).encode()))

    def test_pin_has_complete_archive_provenance_and_only_approved_successor(self):
        self.assertEqual(2, self.pin["schema_version"])
        self.assertEqual("compatibility/bedrock/SFL_GEYSER_RP_experimental_v1.0.3_complete.zip",
                         self.pin["archive_path"])
        self.assertEqual(["v4.1.76"], self.pin["carry_forward_tags"])
        self.assertEqual(2390264, self.pin["size_bytes"])
        self.assertEqual("60fb9fcfe19e7e5644ff7202fd83bcd2b73b9f7685f3a57797d73877153c014c", self.pin["sha256"])
        self.assertEqual([664289959, 664360404], [source["asset_id"] for source in self.pin["source_assets"]])
        self.assertEqual(list(subject.SOURCE_ASSETS), self.pin["source_assets"])
        self.assertFalse({"release_tag", "release_id", "asset_id"} & set(self.pin))

    def test_pin_rejects_invalid_types_and_broad_targets(self):
        cases = {"schema_version": True, "repository": "other/repository", "release_tag": "v4.1.75",
                 "asset_name": "unreviewed.zip", "release_id": 415923695, "asset_id": 664360404,
                 "archive_path": "../unreviewed.zip", "size_bytes": "2390264",
                 "sha256": "invalid", "carry_forward_tags": ["*"],
                 "stability": "stable"}
        for key, value in cases.items():
            with self.subTest(key=key):
                pin = copy.deepcopy(self.pin)
                pin[key] = value
                with self.assertRaises(ValueError):
                    subject.load_pin(self.json_path("pin.json", pin))

    def test_pin_rejects_duplicate_or_source_target(self):
        for tags in ([], ["v4.1.76", "v4.1.76"], ["v4.1.75"], ["v4.1.77"], ["v4.1.76", "v4.1.77"], None):
            with self.subTest(tags=tags):
                pin = dict(self.pin, carry_forward_tags=tags)
                with self.assertRaises(ValueError):
                    subject.load_pin(self.json_path("pin.json", pin))

    def test_provenance_requires_both_exact_sources_in_order(self):
        sources = self.pin["source_assets"]
        for value in (None, {}, [], sources[:1], sources + sources[:1], list(reversed(sources))):
            with self.subTest(sources=value), self.assertRaises(ValueError):
                subject.load_pin(self.json_path("pin.json", dict(self.pin, source_assets=value)))
        for index in range(2):
            for field, value in (("release_tag", "v4.1.74"), ("release_id", True),
                                 ("release_id", 415923695.0), ("asset_id", 999),
                                 ("asset_name", "different.zip"), ("size_bytes", 0),
                                 ("sha256", "f" * 64), ("repository", "other/repository")):
                pin = copy.deepcopy(self.pin)
                pin["source_assets"][index][field] = value
                with self.subTest(index=index, field=field, value=value), self.assertRaises(ValueError):
                    subject.load_pin(self.json_path("pin.json", pin))

    def test_repository_archive_path_cannot_redirect_to_removed_source_or_external_file(self):
        for path in ("/tmp/pack.zip", "compatibility/bedrock/../pack.zip",
                     "https://example.invalid/pack.zip", "compatibility/bedrock/GEYSER_SFL_RP_v0.0.2.zip"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "archive path"):
                subject.load_pin(self.json_path("pin.json", dict(self.pin, archive_path=path)))

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            subject.json_data('{"asset_id": 1, "asset_id": 2}')

    def test_exact_source_release_is_accepted(self):
        # The current release contains only the overlay; the historical base is absent.
        subject.verify_source_release(self.json_path("source.json", self.source()), self.pin)

    def test_historical_source_metadata_cannot_substitute_for_current_overlay(self):
        with self.assertRaisesRegex(ValueError, "Release is missing"):
            subject.verify_source_release(self.json_path("source.json", self.source(index=0)), self.pin)

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
        path = self.json_path("target.json", self.target())
        subject.verify_target_release(path, "v4.1.76", self.pin)
        for tag in ("v4.1.75", "v4.1.77", "latest"):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "not approved"):
                subject.verify_target_release(path, tag, self.pin)

    def test_substituted_or_missing_target_asset_is_rejected(self):
        for change in ({"digest": "sha256:" + "f" * 64}, {"size": 1}, {"state": "starter"},
                       {"name": "Geyser-Spigot-RP-alpha-v0.0.3.zip"}):
            with self.subTest(change=change):
                release = self.target()
                release["assets"][0].update(change)
                with self.assertRaises(ValueError):
                    subject.verify_target_release(self.json_path("target.json", release), "v4.1.76", self.pin)

    def test_overlay_cannot_replace_complete_target_even_with_valid_source_metadata(self):
        release = self.source()
        release.update(id=987, tag_name="v4.1.76")
        with self.assertRaisesRegex(ValueError, "Release is missing"):
            subject.verify_target_release(self.json_path("target.json", release), "v4.1.76", self.pin)

    def test_exact_fixture_with_enclosing_pack_directory_passes(self):
        report = self.verify_entries(self.entries)
        self.assertEqual({"mapping_files": 23, "resource_packs": 3, "pack_files": 8}, report)

    def test_root_pack_manifest_is_also_supported(self):
        entries = [(name.removeprefix("SFB-RP/"), data) for name, data in self.pack_entries]
        self.verify_entries(self.pack_outer(entries))

    def test_outer_size_and_digest_are_both_required(self):
        path, pin = self.zip_fixture()
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            subject.verify_zip(path, dict(pin, size_bytes=pin["size_bytes"] + 1))
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            subject.verify_zip(path, dict(pin, sha256="f" * 64))

    def test_missing_mapping_mcpack_or_installation_guide_is_rejected(self):
        for missing in (self.entries[0][0], subject.VALHALLA_MAPPING, *subject.SKULL_MAPPINGS,
                        *subject.MCPACKS, *subject.DOCUMENT_FILES):
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                self.verify_entries([entry for entry in self.entries if entry[0] != missing])

    def test_incomplete_overlay_missing_all_21_base_mapping_files_is_rejected(self):
        base = {subject.MAPPINGS + name for name in subject.BASE_MAPPING_NAMES} | {subject.SKULL_MAPPING}
        self.assertEqual(21, len(base))
        with self.assertRaisesRegex(ValueError, "Unexpected files"):
            self.verify_entries([entry for entry in self.entries if entry[0] not in base])

    def test_installation_guides_require_nonempty_utf8(self):
        for name in subject.DOCUMENT_FILES:
            for data in (b"", b" \n\t", b"\xff"):
                with self.subTest(name=name, data=data), self.assertRaises(ValueError):
                    self.verify_entries(self.replace_entry(name, data))

    def test_extra_drop_in_files_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected files"):
            self.verify_entries(self.entries + [("Geyser-Spigot/config.yml", b"unapproved")])

    def test_expected_mapping_names_cannot_be_substituted_at_the_same_count(self):
        for name in (self.entries[0][0], subject.VALHALLA_MAPPING, *subject.SKULL_MAPPINGS):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unexpected files"):
                self.verify_entries([((subject.MAPPINGS + "other.json") if key == name else key, data)
                                     for key, data in self.entries])

    def test_unknown_empty_drop_in_directory_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected directories"):
            self.verify_entries(self.entries + [("Geyser-Spigot/extensions/", b"")])

    def test_invalid_or_empty_custom_mapping_is_rejected(self):
        for data in (b"not json", b'{"format_version":"1","items":{}}',
                     b'{"format_version":"2","items":{"minecraft:stone":[]}}',
                     b'{"format_version":"1","items":{},"items":{"minecraft:stone":[]}}'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.verify_entries([(self.entries[0][0], data)] + self.entries[1:])

    def test_valhalla_format_and_top_level_types_are_required(self):
        cases = [dict(self.valhalla, format_version=value) for value in ("2", 2.0, True, None)]
        cases += [dict(self.valhalla, items=value) for value in ([], {}, None)]
        cases.append(dict(self.valhalla, unreviewed=True))
        for mapping in cases:
            with self.subTest(mapping=mapping), self.assertRaisesRegex(ValueError, "format-2"):
                self.verify_mapping(subject.VALHALLA_MAPPING, mapping)

    def test_valhalla_definition_identity_and_list_shape_are_required(self):
        for field, value in (("type", "other"), ("model", "minecraft:dirt"),
                             ("bedrock_identifier", "other:example"), ("bedrock_identifier", 7)):
            mapping = copy.deepcopy(self.valhalla)
            mapping["items"]["minecraft:stone"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "definition"):
                self.verify_mapping(subject.VALHALLA_MAPPING, mapping)
        for value in ({}, [], "definition", [None]):
            mapping = copy.deepcopy(self.valhalla)
            mapping["items"]["minecraft:stone"] = value
            with self.subTest(entries=value), self.assertRaises(ValueError):
                self.verify_mapping(subject.VALHALLA_MAPPING, mapping)

    def test_duplicate_valhalla_bedrock_identifiers_are_rejected(self):
        mapping = copy.deepcopy(self.valhalla)
        mapping["items"]["minecraft:stone"] *= 2
        with self.assertRaisesRegex(ValueError, "Duplicate Valhalla Bedrock identifier"):
            self.verify_mapping(subject.VALHALLA_MAPPING, mapping)

    def test_valhalla_predicates_reject_wrong_fields_types_and_nonfinite_numbers(self):
        changes = (("type", "other"), ("property", "other"), ("threshold", True), ("threshold", "1"),
                   ("threshold", 0), ("threshold", float("nan")), ("threshold", float("inf")),
                   ("scale", True), ("scale", 2.0), ("index", False), ("index", 0.0), ("index", 1))
        for field, value in changes:
            mapping = copy.deepcopy(self.valhalla)
            mapping["items"]["minecraft:stone"][0]["predicate"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.verify_mapping(subject.VALHALLA_MAPPING, mapping)
        for value in (None, {}, [], [None], [{"type": "match", "property": "charge_type", "value": "arrow"}]):
            mapping = copy.deepcopy(self.valhalla)
            mapping["items"]["minecraft:stone"][0]["predicate"] = value
            with self.subTest(predicates=value), self.assertRaises(ValueError):
                self.verify_mapping(subject.VALHALLA_MAPPING, mapping)

    def test_reviewed_valhalla_charge_and_armor_options_pass(self):
        for charge in ("arrow", "rocket"):
            mapping = copy.deepcopy(self.valhalla)
            entry = mapping["items"]["minecraft:stone"][0]
            entry["predicate"].append({"type": "match", "property": "charge_type", "value": charge})
            entry["bedrock_options"].update(display_handheld=True,
                                            tags=["minecraft:is_armor", "minecraft:trimmable_armors"])
            with self.subTest(charge=charge):
                self.verify_mapping(subject.VALHALLA_MAPPING, mapping)

    def test_valhalla_options_reject_wrong_types_and_unknown_fields(self):
        changes = (("icon", 7), ("icon", "other_example"), ("display_handheld", "true"),
                   ("display_handheld", 1), ("tags", "minecraft:is_armor"), ("tags", []),
                   ("tags", ["other"]), ("tags", ["minecraft:is_armor"] * 2), ("unknown", True))
        for field, value in changes:
            mapping = copy.deepcopy(self.valhalla)
            mapping["items"]["minecraft:stone"][0]["bedrock_options"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.verify_mapping(subject.VALHALLA_MAPPING, mapping)

    def test_skull_schema_rejects_wrong_formats_fields_and_identity_types(self):
        cases = [dict(self.skulls, format_version=value) for value in ("1", 1.0, True, 2)]
        cases += [dict(self.skulls, skulls=value) for value in ([], {}, None)]
        cases.append(dict(self.skulls, items={}))
        for name in subject.SKULL_MAPPINGS:
            for mapping in cases:
                with self.subTest(name=name, mapping=mapping), self.assertRaises(ValueError):
                    self.verify_mapping(name, mapping)
            for field, value in (("username", ["unreviewed"]), ("uuid", None), ("profile", {}),
                                 ("skin_hash", []), ("skin_hash", "abc123"), ("skin_hash", [True]),
                                 ("skin_hash", ["abc123"] * 2), ("skin_hash", ["xyz"]),
                                 ("skin_hash", ["a" * 65])):
                mapping = copy.deepcopy(self.skulls)
                mapping["skulls"][field] = value
                with self.subTest(name=name, field=field, value=value), self.assertRaises(ValueError):
                    self.verify_mapping(name, mapping)

    def test_skull_hashes_need_not_be_64_hex_digits(self):
        mapping = copy.deepcopy(self.skulls)
        mapping["skulls"]["skin_hash"] = ["abc123", "b" * 57, "c" * 64]
        self.verify_mapping(subject.SKULL_MAPPING, mapping)

    def test_overlay_skull_hashes_cannot_duplicate_base_identities(self):
        with self.assertRaisesRegex(ValueError, "Duplicate skull skin hashes across"):
            self.verify_mapping(subject.NEW_SKULL_MAPPING, self.skulls)

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
        for name, entries in ((subject.MCPACK, self.pack_entries),
                              (subject.VALHALLA_PACK, self.valhalla_pack_entries),
                              (subject.STAT_ICONS_PACK, self.stat_pack_entries)):
            pack = archive_bytes(entries).replace(b"fixture-pixel", b"fixture-false", 1)
            with self.subTest(pack=name), self.assertRaisesRegex(ValueError, "CRC"):
                self.verify_entries(self.replace_entry(name, pack))

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

    def test_stat_icon_pack_requires_both_font_pages_and_exact_layout(self):
        for missing in ("manifest.json", "font/glyph_ED.png", "font/glyph_EE.png", "pack_icon.png"):
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                self.verify_entries(self.pack_outer([entry for entry in self.stat_pack_entries if entry[0] != missing],
                                                   subject.STAT_ICONS_PACK))
        with self.assertRaisesRegex(ValueError, "stat-icon font layout"):
            self.verify_entries(self.pack_outer(self.stat_pack_entries + [("textures/item.png", b"fixture-pixel")],
                                               subject.STAT_ICONS_PACK))

    def test_added_pack_requires_root_manifest_and_resource_module(self):
        for entries in (self.valhalla_pack_entries[1:], self.valhalla_pack_entries[:1],
                        [("enclosing/" + name, data) for name, data in self.valhalla_pack_entries],
                        [("manifest.json", json.dumps(dict(self.manifest, modules=[])).encode()),
                         self.valhalla_pack_entries[1]]):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                self.verify_entries(self.pack_outer(entries, subject.VALHALLA_PACK))

    def test_invalid_nested_json_is_rejected_in_both_texture_packs(self):
        for name, entries in ((subject.MCPACK, self.pack_entries),
                              (subject.VALHALLA_PACK, self.valhalla_pack_entries)):
            for invalid in (b"not json", b'{"x":1,"x":2}', b'{"x":NaN}'):
                with self.subTest(pack=name, invalid=invalid), self.assertRaises(ValueError):
                    self.verify_entries(self.pack_outer(entries + [("models/example.json", invalid)], name))

    def test_material_json_requires_complete_unique_finite_json(self):
        name = "SFB-RP/materials/entity.material"
        self.verify_entries(self.pack_outer(self.pack_entries + [(name, b'{"materials":{"version":"1.0.0"}}')]))
        for invalid in (b'{"materials":{"version":"1.0.0"}', b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.verify_entries(self.pack_outer(self.pack_entries + [(name, invalid)]))

    def test_cli_checks_approved_target_before_publication_without_metadata(self):
        pin_path = self.json_path("pin.json", self.pin)
        for tag, expected in (("v4.1.76", 0), ("v4.1.77", 1)):
            with self.subTest(tag=tag):
                result = subprocess.run([*PYTHON, str(SCRIPT), str(ROOT), "--pin", str(pin_path),
                                         "--target-tag", tag], capture_output=True, text=True, check=False)
                self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
                if expected:
                    self.assertIn("target release tag is not approved", result.stderr)
                    self.assertNotIn("verification passed", result.stdout)
                else:
                    self.assertIn("verification passed", result.stdout)

    def test_cli_complete_local_zip_needs_no_source_release_or_historical_download(self):
        path, pin = self.zip_fixture()
        pin_path = self.json_path("pin.json", pin)
        # This isolated directory contains only the complete fixture and pin, with
        # no origin metadata, v0.0.2 download, or network operation available to the helper.
        self.assertEqual({"fixture.zip", "pin.json"}, {entry.name for entry in self.directory.iterdir()})
        result = subprocess.run([*PYTHON, str(SCRIPT), str(self.directory), "--pin", str(pin_path),
                                 "--zip", str(path), "--target-tag", "v4.1.76"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("verification passed", result.stdout)

    def test_cli_accepts_all_checks_and_target_metadata_requires_tag(self):
        path, pin = self.zip_fixture()
        pin_path = self.json_path("pin.json", pin)
        source_path = self.json_path("source.json", self.source())
        target_path = self.json_path("target.json", self.target(pin))
        command = [*PYTHON, str(SCRIPT), str(ROOT), "--pin", str(pin_path), "--release-json", str(source_path),
                   "--zip", str(path), "--target-release-json", str(target_path), "--target-tag", "v4.1.76"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("verification passed", result.stdout)
        result = subprocess.run(command[:-2], capture_output=True, text=True, check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("requires --target-tag", result.stderr)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
