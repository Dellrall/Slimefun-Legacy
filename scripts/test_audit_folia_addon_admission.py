#!/usr/bin/env python3

from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import audit_folia_addon_admission as audit


def plugin_jar(descriptor_name: str, folia_line: str | None) -> bytes:
    buffer = io.BytesIO()
    descriptor = "name: Fixture\nversion: 1.0\n"
    if folia_line is not None:
        descriptor += folia_line + "\n"
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(descriptor_name, descriptor)
    return buffer.getvalue()


class TestFoliaAddonAdmissionAudit(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "bundle.zip"

    def write_bundle(self, rows, blobs, *, revision=137, duplicate_entry=False):
        manifest = {
            "bundle_revision": revision,
            "core_source_commit": "a" * 40,
            "addons": rows,
        }
        with zipfile.ZipFile(self.bundle, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("SF_ADDON_MANIFEST.json", json.dumps(manifest))
            for name, blob in blobs.items():
                zf.writestr(name, blob)
            if duplicate_entry:
                first = next(iter(blobs.items()))
                zf.writestr(first[0], first[1])

    def test_classifies_true_false_and_undeclared(self):
        rows = [
            {"repository": "example/true", "commit": "1" * 40, "jar": "True.jar"},
            {"repository": "example/false", "commit": "2" * 40, "jar": "False.jar"},
            {"repository": "example/missing", "commit": "3" * 40, "jar": "Missing.jar"},
        ]
        blobs = {
            "True.jar": plugin_jar("plugin.yml", "folia-supported: true"),
            "False.jar": plugin_jar("plugin.yml", "folia-supported: FALSE"),
            "Missing.jar": plugin_jar("paper-plugin.yml", None),
        }
        self.write_bundle(rows, blobs)
        report = audit.audit(self.bundle)
        self.assertEqual(report["counts"], {"declared_true": 1, "declared_false": 1, "undeclared": 1})
        by_repo = {row["repository"]: row for row in report["addons"]}
        self.assertEqual(by_repo["example/true"]["admission"], "declared-true")
        self.assertEqual(by_repo["example/false"]["admission"], "declared-false")
        self.assertEqual(by_repo["example/missing"]["admission"], "undeclared")
        self.assertEqual(report["scope"], "descriptor-admission-only")

    def test_bundle_manifest_mismatch_refused(self):
        rows = [{"repository": "example/a", "commit": "1" * 40, "jar": "A.jar"}]
        blobs = {
            "A.jar": plugin_jar("plugin.yml", "folia-supported: true"),
            "Extra.jar": plugin_jar("plugin.yml", "folia-supported: true"),
        }
        self.write_bundle(rows, blobs)
        with self.assertRaisesRegex(ValueError, "Bundle/manifest JAR mismatch"):
            audit.audit(self.bundle)

    def test_missing_descriptor_refused(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.txt", "no descriptor")
        rows = [{"repository": "example/a", "commit": "1" * 40, "jar": "A.jar"}]
        self.write_bundle(rows, {"A.jar": raw.getvalue()})
        with self.assertRaisesRegex(ValueError, "No plugin descriptor"):
            audit.audit(self.bundle)

    def test_duplicate_manifest_jar_refused(self):
        rows = [
            {"repository": "example/a", "commit": "1" * 40, "jar": "A.jar"},
            {"repository": "example/b", "commit": "2" * 40, "jar": "A.jar"},
        ]
        self.write_bundle(rows, {"A.jar": plugin_jar("plugin.yml", "folia-supported: true")})
        with self.assertRaisesRegex(ValueError, "duplicate addon JAR"):
            audit.audit(self.bundle)

    def test_duplicate_zip_entry_refused(self):
        rows = [{"repository": "example/a", "commit": "1" * 40, "jar": "A.jar"}]
        self.write_bundle(
            rows,
            {"A.jar": plugin_jar("plugin.yml", "folia-supported: true")},
            duplicate_entry=True,
        )
        with self.assertRaisesRegex(ValueError, "duplicate ZIP entries"):
            audit.audit(self.bundle)


if __name__ == "__main__":
    unittest.main()
