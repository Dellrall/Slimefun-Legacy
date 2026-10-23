#!/usr/bin/env python3
"""Offline conservation and rejection tests for MagicExpansion-only r150 release."""
import hashlib
import io
import json
import unittest
import zipfile

from prepare_magic_r150_release_asset import (
    HUD, HUD_SOURCE, MAGIC, NETWORKS, NETWORKS_SOURCE, NEW_SOURCE, OLD_SOURCE, NAME,
    rebuild, sha,
)


def pack(files):
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, contents in files.items():
            out.writestr(name, contents)
    return result.getvalue()


class R150ConservationTest(unittest.TestCase):
    def setUp(self):
        self.old_jar = pack({"plugin.yml": "name: magicexpansion\nversion: 1.1.17\n"})
        self.new_jar = pack({"plugin.yml": "name: magicexpansion\nversion: 1.1.18\n",
                             "example/ResourceMachine.class": b"synthetic"})
        known = [
            (MAGIC, "SF_MagicExpansion1.1.17.jar", "1.1.17", OLD_SOURCE),
            (NETWORKS, "SF_Networks1.0.61.jar", "1.0.61", NETWORKS_SOURCE),
            (HUD, "SF_SlimeHUD2.0.7.jar", "2.0.7", HUD_SOURCE),
            ("wickidcow/SF_InfinityExpansion2", "SF_InfinityExpansion2.0.15.jar",
             "2.0.15", "1" * 40)
        ]
        known += [(f"wickidcow/SF_Addon{i:02}", f"SF_Addon{i:02}1.0.0.jar",
                   "1.0.0", f"{i:040x}") for i in range(1, 42)]
        rows = []
        self.files = {"README.txt": b"Keep all unrelated files untouched\n"}
        for repo, filename, version, commit in known:
            data = self.old_jar if repo == MAGIC else (repo + "\n").encode()
            self.files[filename] = data
            rows.append(dict(repository=repo, jar=filename, source_jar=filename,
                             version=version, commit=commit, sha256=sha(data)))
        manifest = dict(bundle=NAME, bundle_revision=149, addons=rows,
                        core_source_commit="9" * 40)
        self.files["SF_ADDON_MANIFEST.json"] = json.dumps(manifest).encode()
        self.files["SHA256SUMS.txt"] = ("\n".join(sorted(
            f'{r["sha256"]}  {r["jar"]}' for r in rows)) + "\n").encode()
        self.base = pack(self.files)
        self.matrix = {"bundle_revision": 150, "addons": [
            {"repository": r["repository"],
             "source_commit": NEW_SOURCE if r["repository"] == MAGIC else r["commit"]}
            for r in rows]}

    def run_rebuild(self):
        return rebuild(self.base, self.new_jar, self.matrix,
                       sha(self.base), sha(self.new_jar))

    def test_only_one_jar_and_two_metadata_files_change(self):
        rebuilt, report = self.run_rebuild()
        with zipfile.ZipFile(io.BytesIO(rebuilt)) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(len([n for n in z.namelist() if n.endswith(".jar")]), 45)
            self.assertNotIn("SF_MagicExpansion1.1.17.jar", z.namelist())
            self.assertEqual(z.read("SF_MagicExpansion1.1.18.jar"), self.new_jar)
            manifest = json.loads(z.read("SF_ADDON_MANIFEST.json"))
            self.assertEqual(manifest["bundle_revision"], 150)
            self.assertEqual(manifest["core_source_commit"], "9" * 40)
            for name in self.files:
                if name not in ("SF_MagicExpansion1.1.17.jar",
                                "SF_ADDON_MANIFEST.json", "SHA256SUMS.txt"):
                    self.assertEqual(z.read(name), self.files[name], name)
            checks = sorted(z.read("SHA256SUMS.txt").decode().splitlines())
            self.assertEqual(len(checks), 45)
        self.assertEqual(report["other_addon_jars_byte_identical"], 44)

    def test_stale_or_changed_base_is_rejected(self):
        for invalid in ("0" * 64, "unverified"):
            with self.subTest(digest=invalid), self.assertRaises(ValueError):
                rebuild(self.base, self.new_jar, self.matrix, invalid, sha(self.new_jar))

    def test_wrong_magic_binary_or_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "JAR checksum mismatch"):
            rebuild(self.base, self.new_jar, self.matrix, sha(self.base), "0" * 64)
        matrix = json.loads(json.dumps(self.matrix))
        matrix["addons"][0]["source_commit"] = OLD_SOURCE
        with self.assertRaisesRegex(ValueError, "source pin mismatch"):
            rebuild(self.base, self.new_jar, matrix, sha(self.base), sha(self.new_jar))

    def test_unrelated_addon_pin_mutation_is_rejected(self):
        matrix = json.loads(json.dumps(self.matrix))
        matrix["addons"][1]["source_commit"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "Unrelated source pin"):
            rebuild(self.base, self.new_jar, matrix, sha(self.base), sha(self.new_jar))

    def test_invalid_revision_rejected(self):
        matrix = json.loads(json.dumps(self.matrix))
        matrix["bundle_revision"] = 151
        with self.assertRaisesRegex(ValueError, "exact r150"):
            rebuild(self.base, self.new_jar, matrix, sha(self.base), sha(self.new_jar))

    def test_older_magic_or_wrong_plugin_rejected(self):
        with self.assertRaisesRegex(ValueError, "version must"):
            rebuild(self.base, self.old_jar, self.matrix, sha(self.base), sha(self.old_jar))
        wrong = pack({"plugin.yml": "name: Other\nversion: 1.1.18\n",
                      "x/ResourceMachine.class": b"x"})
        with self.assertRaisesRegex(ValueError, "identity changed"):
            rebuild(self.base, wrong, self.matrix, sha(self.base), sha(wrong))


if __name__ == "__main__":
    unittest.main()
