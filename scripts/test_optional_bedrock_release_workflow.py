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
BEDROCK = "GEYSER_SFL_RP_Experimental_v0.0.1.zip"
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
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr("Geyser-Spigot/packs/SlimefunBedrockRP.mcpack", nested.getvalue())
        for index in range(20):
            archive.writestr(f"Geyser-Spigot/custom_mappings/test-{index}.json", json.dumps({
                "format_version": "1",
                "items": {"minecraft:stick": [{"name": f"offline_fixture_{index}", "custom_model_data": index + 1}]},
            }))
    return outer.getvalue()


FAKE_GH = r'''#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
args = sys.argv[1:]
with open(os.environ['MOCK_CALLS'], 'a') as calls:
    calls.write(json.dumps(args) + '\n')
repo = 'wickidcow/Slimefun-Legacy'
target = 'v4.1.76'
state_path = pathlib.Path(os.environ['MOCK_TARGET'])
state = json.loads(state_path.read_text())
if args == ['api', f'repos/{repo}/releases/tags/v4.1.75']:
    print(pathlib.Path(os.environ['MOCK_SOURCE']).read_text())
elif args == ['api', f'repos/{repo}/releases/tags/{target}']:
    print(json.dumps(state))
elif args[:3] == ['release', 'download', 'v4.1.75']:
    if args[args.index('--repo') + 1] != repo:
        sys.exit(12)
    name = args[args.index('--pattern') + 1]
    if name != 'GEYSER_SFL_RP_Experimental_v0.0.1.zip':
        sys.exit(13)
    directory = pathlib.Path(args[args.index('--dir') + 1])
    if not directory.resolve().is_relative_to(pathlib.Path.cwd()):
        sys.exit(14)
    directory.mkdir(exist_ok=True)
    shutil.copyfile(os.environ['MOCK_DOWNLOAD'], directory / name)
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
        self.download = self.directory / "source-pack.zip"
        self.download.write_bytes(self.archive)
        source_asset = self.asset(BEDROCK, self.pin["asset_id"])
        self.source = {"id": self.pin["release_id"], "tag_name": self.pin["release_tag"],
                       "draft": False, "prerelease": False, "assets": [source_asset]}
        self.target = {"id": 900000076, "tag_name": TARGET_TAG, "draft": False, "prerelease": False,
                       "assets": [self.asset(CORE, 1), self.asset(BUNDLE, 2), self.asset(JAVA_PACK, 3),
                                  self.asset(BEDROCK, 4)]}
        self.write_json("source.json", self.source)
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
            "MOCK_SOURCE": str(self.directory / "source.json"),
            "MOCK_TARGET": str(self.directory / "target.json"),
            "MOCK_DOWNLOAD": str(self.download), "MOCK_RELEASE_EXISTS": "1",
        }

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

    def test_verified_origin_bytes_are_staged_unchanged(self):
        result = self.run_step("Require pinned optional Bedrock resource pack")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(self.archive, (self.directory / "dist" / BEDROCK).read_bytes())
        self.assertEqual(["api", f"repos/{REPOSITORY}/releases/tags/v4.1.75"], self.calls()[0])
        self.assertEqual(["release", "download", "v4.1.75"], self.calls()[1][:3])
        self.assertEqual([], self.deletion_names())
        self.assertIn("Requires Geyser", (self.directory / "summary.md").read_text())

    def test_changed_source_metadata_or_download_never_stages_pack(self):
        original = json.loads(json.dumps(self.source))
        for change in ("asset_id", "digest", "size", "zip_bytes"):
            with self.subTest(change=change):
                source = json.loads(json.dumps(original))
                self.download.write_bytes(self.archive)
                if change == "asset_id":
                    source["assets"][0]["id"] += 1
                elif change == "digest":
                    source["assets"][0]["digest"] = "sha256:" + "0" * 64
                elif change == "size":
                    source["assets"][0]["size"] += 1
                else:
                    self.download.write_bytes(self.archive[:-1] + bytes([self.archive[-1] ^ 1]))
                self.write_json("source.json", source)
                result = self.run_step("Require pinned optional Bedrock resource pack")
                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertFalse((self.directory / "dist" / BEDROCK).exists())
                self.assertEqual([], self.deletion_names())

    def test_unapproved_target_version_refuses_before_download(self):
        self.env["LEGACY_ARTIFACT_VERSION"] = "4.1.77"
        result = self.run_step("Require pinned optional Bedrock resource pack")
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse((self.directory / "dist" / BEDROCK).exists())
        self.assertEqual([], self.calls())

    def test_normalizer_accepts_exact_four_assets_with_new_bedrock_id(self):
        self.assertNotEqual(self.pin["asset_id"], self.target["assets"][-1]["id"])
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
