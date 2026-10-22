#!/usr/bin/env python3
"""Exercise the real Bedrock release shell steps with local GitHub/git doubles."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/reproducible-release.yml"
BEDROCK = "SFL_GEYSER_RP_experimental_v1.0.3_complete.zip"
CORE = "Slimefun-Legacy4.1.76.jar"
BUNDLE = "SF_Addons_1.21.11-26.3.zip"
JAVA_PACK = "SlimefunLegacyRP.zip"
REPOSITORY = "wickidcow/Slimefun-Legacy"
TARGET_TAG = "v4.1.76"


def workflow_block(name: str) -> str:
    section = WORKFLOW.read_text().split("- name: " + name, 1)[1]
    lines = section.split("        run: |\n", 1)[1].splitlines()
    result = []
    for line in lines:
        if line and not line.startswith("          "):
            break
        result.append(line[10:] if line else "")
    return "\n".join(result) + "\n"


def fixture_zip() -> bytes:
    # Independent, small structure fixture; no network or production pack needed.
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as pack:
        pack.writestr("manifest.json", json.dumps({
            "format_version": 2,
            "header": {"name": "Offline test", "description": "Offline fixture", "version": [0, 0, 1],
                       "uuid": "10000000-0000-0000-0000-000000000001", "min_engine_version": [1, 21, 0]},
            "modules": [{"type": "resources", "version": [0, 0, 1],
                         "uuid": "10000000-0000-0000-0000-000000000002"}],
        }))
        pack.writestr("textures/items/test.png", base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9GQAAAAASUVORK5CYII="))
    stat_icons = io.BytesIO()
    with zipfile.ZipFile(nested) as source, zipfile.ZipFile(stat_icons, "w") as pack:
        pack.writestr("manifest.json", source.read("manifest.json"))
        for name in ("pack_icon.png", "font/glyph_ED.png", "font/glyph_EE.png"):
            pack.writestr(name, source.read("textures/items/test.png"))
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr("README.txt", "Original overlay fixture\n")
        archive.writestr("INSTALL.md", "Complete installation fixture: Geyser and matching mappings are required.\n")
        for name in ("SlimefunBedrockRP_1.0.1.mcpack", "Albion_ValhallaMMO_Bedrock_1.0.1.mcpack",
                     "Albion_ValhallaMMO_Stat_Icons_1.0.0.mcpack"):
            content = stat_icons.getvalue() if "Stat_Icons" in name else nested.getvalue()
            directory = "optional/" if "Stat_Icons" in name else "packs/"
            archive.writestr(directory + name, content)
        legacy_mappings = (
            "SF-Androids.json", "SF-Armors.json", "SF-Basic_Machines.json", "SF-Cargo.json",
            "SF-EG-Drinks.json", "SF-EG-Food.json", "SF-Energy&Electricity.json", "SF-Food.json",
            "SF-Gps.json", "SF-Gui.json", "SF-Items.json", "SF-Magical_Gadgets.json",
            "SF-Magical_Items.json", "SF-Resources.json", "SF-Talisman-I.json", "SF-Talisman-II.json",
            "SF-Technical_Components.json", "SF-Tools.json", "SF-Weapons.json", "SlimefunItems.json",
        )
        for index, name in enumerate(legacy_mappings):
            archive.writestr("custom_mappings/" + name, json.dumps({
                "format_version": "1",
                "items": {"minecraft:stick": [{"name": f"offline_fixture_{index}", "custom_model_data": index + 1}]},
            }))
        archive.writestr("custom_mappings/albion_valhallammo_mappings.json", json.dumps({
            "format_version": 2,
            "items": {"minecraft:stick": [{"type": "definition", "model": "minecraft:stick",
                                            "bedrock_identifier": "albion_valhalla:offline_fixture",
                                            "predicate": [{"type": "range_dispatch", "property": "custom_model_data",
                                                           "threshold": 3510001.0, "scale": 1.0, "index": 0}],
                                            "bedrock_options": {"icon": "albion_valhalla_offline_fixture"}}]},
        }))
        archive.writestr("custom_mappings/migrated-custom-skulls.json", json.dumps({
            "format_version": 1,
            "skulls": {"username": [], "uuid": [], "profile": [], "skin_hash": ["a" * 64]},
        }))
        archive.writestr("custom_mappings/albion_slimefun_legacy_skulls.json", json.dumps({
            "format_version": 1,
            "skulls": {"username": [], "uuid": [], "profile": [], "skin_hash": ["b" * 64]},
        }))
    return outer.getvalue()


FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['MOCK_CALLS'], 'a') as calls:
    calls.write(json.dumps(args) + '\n')
repo = 'wickidcow/Slimefun-Legacy'
target = 'v4.1.76'
state_path = pathlib.Path(os.environ['MOCK_TARGET'])
state = json.loads(state_path.read_text())
if args == ['api', f'repos/{repo}/releases/tags/{target}']:
    print(json.dumps(state))
elif args[:3] == ['release', 'view', target]:
    if '--json' in args:
        print('\n'.join(a['name'] for a in state['assets']))
    elif os.environ.get('MOCK_RELEASE_EXISTS') != '1':
        sys.exit(1)
elif args[:3] == ['release', 'delete-asset', target]:
    name = args[3]
    old_length = len(state['assets'])
    state['assets'] = [a for a in state['assets'] if a['name'] != name]
    if len(state['assets']) != old_length - 1:
        sys.exit(15)
    state_path.write_text(json.dumps(state))
elif args[:2] in (['release', 'create'], ['release', 'upload']):
    if args[2] != target or args[args.index('--repo') + 1] != repo:
        sys.exit(16)
    for name in args[3:args.index('--repo')]:
        if not pathlib.Path(name).is_file():
            sys.exit(17)
elif args[:3] == ['release', 'edit', target]:
    pass
else:
    sys.stderr.write('Unexpected fake gh invocation: ' + repr(args))
    sys.exit(18)
'''

FAKE_GIT = r'''#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
if args == ['rev-list', '-n', '1', 'v4.1.76']:
    print(os.environ['GITHUB_SHA'])
elif args == ['rev-parse', '-q', '--verify', 'refs/tags/v4.1.76']:
    sys.exit(1)
else:
    sys.stderr.write('Unexpected fake git invocation: ' + repr(args))
    sys.exit(19)
'''


class BedrockReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bedrock-release-shell-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        for directory in ("mockbin", "scripts", "compatibility", "dist", "runner", "docs/releases"):
            (self.directory / directory).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "scripts/verify_release_bedrock_pack.py", self.directory / "scripts")
        self.archive = fixture_zip()
        self.pin = json.loads((ROOT / "compatibility/bedrock-resource-pack-release.json").read_text())
        self.pin.update(size_bytes=len(self.archive), sha256=hashlib.sha256(self.archive).hexdigest())
        self.write_json("compatibility/bedrock-resource-pack-release.json", self.pin)
        self.checked_in_pack = self.directory / self.pin["archive_path"]
        self.checked_in_pack.parent.mkdir(parents=True, exist_ok=True)
        self.checked_in_pack.write_bytes(self.archive)
        self.target = {"id": 900000076, "tag_name": TARGET_TAG, "draft": False, "prerelease": False,
                       "assets": [self.asset(CORE, 1), self.asset(BUNDLE, 2), self.asset(JAVA_PACK, 3),
                                  self.asset(BEDROCK, 4)]}
        self.write_json("target.json", self.target)
        (self.directory / "docs/releases/4.1.76.md").write_text("Offline release fixture\n")
        for filename in (CORE, BUNDLE, JAVA_PACK):
            (self.directory / "dist" / filename).write_bytes(b"offline release artifact fixture")
        for filename, content in (("gh", FAKE_GH), ("git", FAKE_GIT)):
            path = self.directory / "mockbin" / filename
            path.write_text(content)
            path.chmod(0o755)
        self.env = {
            "PATH": str(self.directory / "mockbin") + os.pathsep + os.path.dirname(sys.executable) + ":/usr/bin:/bin",
            "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_SHA": "a" * 40,
            "GITHUB_STEP_SUMMARY": str(self.directory / "summary.md"),
            "RUNNER_TEMP": str(self.directory / "runner"), "LEGACY_ARTIFACT_VERSION": "4.1.76",
            "BEDROCK_PACK_PIN": "compatibility/bedrock-resource-pack-release.json",
            "OPTIONAL_BEDROCK_PACK": BEDROCK, "OUTPUT_NAME": CORE,
            "CANONICAL_ADDON_BUNDLE": BUNDLE, "CANONICAL_RESOURCE_PACK": JAVA_PACK,
            "MOCK_CALLS": str(self.directory / "calls.jsonl"),
            "MOCK_TARGET": str(self.directory / "target.json"),
            "MOCK_RELEASE_EXISTS": "1",
        }
        if sys.flags.optimize:
            self.env["PYTHONOPTIMIZE"] = str(sys.flags.optimize)

    def asset(self, name: str, identifier: int) -> dict:
        return {"name": name, "id": identifier, "state": "uploaded",
                "size": self.pin["size_bytes"] if name == BEDROCK else 100,
                "digest": "sha256:" + (self.pin["sha256"] if name == BEDROCK else "b" * 64)}

    def write_json(self, name: str, value: dict):
        (self.directory / name).write_text(json.dumps(value))

    def run_step(self, name: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", "-c", workflow_block(name)], cwd=self.directory, env=self.env,
                              capture_output=True, text=True, timeout=15)

    def calls(self) -> list:
        path = self.directory / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def deletion_names(self) -> list:
        return [call[3] for call in self.calls() if call[:2] == ["release", "delete-asset"]]

    def test_verified_checked_in_bytes_are_staged_without_mutable_origin_download(self):
        result = self.run_step("Require pinned optional Bedrock resource pack")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(self.archive, (self.directory / "dist" / BEDROCK).read_bytes())
        self.assertEqual([], self.calls())
        self.assertEqual([], self.deletion_names())
        self.assertIn("Requires Geyser", (self.directory / "summary.md").read_text())

    def test_changed_or_missing_checked_in_pack_never_stages(self):
        for change in ("digest", "size", "zip_bytes", "old_asset_name", "missing_archive", "unsafe_archive_path"):
            with self.subTest(change=change):
                pin = json.loads(json.dumps(self.pin))
                self.checked_in_pack.write_bytes(self.archive)
                if change == "digest":
                    pin["sha256"] = "0" * 64
                elif change == "size":
                    pin["size_bytes"] += 1
                elif change == "zip_bytes":
                    self.checked_in_pack.write_bytes(self.archive[:-1] + bytes([self.archive[-1] ^ 1]))
                elif change == "old_asset_name":
                    pin["asset_name"] = "GEYSER_SFL_RP_Experimental_v0.0.1.zip"
                elif change == "unsafe_archive_path":
                    pin["archive_path"] = "../outside.zip"
                else:
                    self.checked_in_pack.unlink()
                self.write_json("compatibility/bedrock-resource-pack-release.json", pin)
                result = self.run_step("Require pinned optional Bedrock resource pack")
                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertFalse((self.directory / "dist" / BEDROCK).exists())
                self.assertEqual([], self.calls())

    def test_unapproved_target_version_refuses_before_download(self):
        self.env["LEGACY_ARTIFACT_VERSION"] = "4.1.77"
        result = self.run_step("Require pinned optional Bedrock resource pack")
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse((self.directory / "dist" / BEDROCK).exists())
        self.assertEqual([], self.calls())

    def test_normalizer_accepts_exact_four_assets_with_new_bedrock_id(self):
        self.assertNotIn(self.target["assets"][-1]["id"],
                         [source["asset_id"] for source in self.pin["source_assets"]])
        result = self.run_step("Normalize and verify release assets")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(self.target, json.loads((self.directory / "target.json").read_text()))
        self.assertEqual([], self.deletion_names())
        self.assertIn("Release assets: exactly four", (self.directory / "summary.md").read_text())

    def test_normalizer_refuses_missing_extra_or_changed_bedrock(self):
        for change in ("missing", "extra", "digest", "size"):
            with self.subTest(change=change):
                target = json.loads(json.dumps(self.target))
                if change == "missing":
                    target["assets"].pop()
                elif change == "extra":
                    target["assets"].append(self.asset("unapproved.zip", 5))
                elif change == "digest":
                    target["assets"][-1]["digest"] = "sha256:" + "0" * 64
                else:
                    target["assets"][-1]["size"] += 1
                self.write_json("target.json", target)
                result = self.run_step("Normalize and verify release assets")
                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertEqual(target, json.loads((self.directory / "target.json").read_text()))
                self.assertEqual([], self.deletion_names())

    def test_normalizer_deletes_only_explicit_existing_legacy_assets(self):
        legacy_names = ["SF_Test1.0.jar", "SFL_AddonsNDependencies.zip"]
        target = json.loads(json.dumps(self.target))
        target["assets"].extend(self.asset(name, index + 10) for index, name in enumerate(legacy_names))
        self.write_json("target.json", target)
        result = self.run_step("Normalize and verify release assets")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(legacy_names, self.deletion_names())
        self.assertEqual(self.target, json.loads((self.directory / "target.json").read_text()))

    def test_both_create_and_upload_receive_the_same_four_paths(self):
        staged = self.run_step("Require pinned optional Bedrock resource pack")
        self.assertEqual(0, staged.returncode, staged.stdout + staged.stderr)
        expected = ["dist/" + name for name in (CORE, BUNDLE, JAVA_PACK, BEDROCK)]
        for existing, action in (("0", "create"), ("1", "upload")):
            with self.subTest(action=action):
                self.env["MOCK_RELEASE_EXISTS"] = existing
                result = self.run_step("Publish reproducible release assets")
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                calls = [call for call in self.calls() if call[:2] == ["release", action]]
                self.assertEqual(1, len(calls))
                call = calls[0]
                self.assertEqual(TARGET_TAG, call[2])
                self.assertEqual(expected, call[3:call.index("--repo")])
                self.assertEqual(REPOSITORY, call[call.index("--repo") + 1])
        self.assertEqual([], self.deletion_names())


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
