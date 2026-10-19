#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import audit_folia_addon_admission as audit
import prepare_folia_addon_runtime as runtime


SOURCE = "a" * 40


def jar_bytes(name: str, folia: bool | None, depend: list[str] | None = None) -> bytes:
    descriptor = [f"name: {name}", "version: 1.0", "main: example.Main"]
    if folia is not None:
        descriptor.append(f"folia-supported: {'true' if folia else 'false'}")
    if depend:
        descriptor.append("depend: [" + ", ".join(depend) + "]")
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("plugin.yml", "\n".join(descriptor) + "\n")
        zf.writestr("example/Main.class", b"fake-class")
    return buffer.getvalue()


class TestPrepareFoliaAddonRuntime(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle.zip"
        self.report = self.root / "admission.json"
        self.output = self.root / "addons"
        self.expected = self.root / "expected.txt"
        self.selection = self.root / "selection.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_bundle(self, records: list[tuple[str, str, bytes]]) -> None:
        manifest_rows = []
        with zipfile.ZipFile(self.bundle, "w", zipfile.ZIP_DEFLATED) as zf:
            for index, (repository, jar_name, blob) in enumerate(records):
                zf.writestr(jar_name, blob)
                manifest_rows.append(
                    {
                        "repository": repository,
                        "commit": f"{index + 1:040x}",
                        "jar": jar_name,
                        "sha256": hashlib.sha256(blob).hexdigest(),
                    }
                )
            zf.writestr(
                "SF_ADDON_MANIFEST.json",
                json.dumps(
                    {
                        "bundle_revision": 142,
                        "core_source_commit": SOURCE,
                        "addons": manifest_rows,
                    }
                ),
            )
        self.report.write_text(json.dumps(audit.audit(self.bundle, SOURCE)), encoding="utf-8")

    def prepare(self) -> dict:
        return runtime.prepare(
            self.bundle,
            self.report,
            self.output,
            self.expected,
            self.selection,
            SOURCE,
        )

    def test_selects_only_declared_true_and_preserves_exact_bytes(self) -> None:
        selected = jar_bytes("AddonA", True, ["Slimefun"])
        excluded = jar_bytes("AddonB", False, ["Slimefun"])
        unknown = jar_bytes("AddonC", None, ["Slimefun"])
        self.write_bundle(
            [
                ("wickidcow/A", "A.jar", selected),
                ("wickidcow/B", "B.jar", excluded),
                ("wickidcow/C", "C.jar", unknown),
            ]
        )

        result = self.prepare()

        self.assertEqual(result["addon_count"], 1)
        self.assertEqual((self.output / "A.jar").read_bytes(), selected)
        self.assertFalse((self.output / "B.jar").exists())
        self.assertFalse((self.output / "C.jar").exists())
        self.assertEqual(self.expected.read_text(encoding="utf-8"), "A.jar\tAddonA\n")

    def test_rejects_bundle_changed_after_descriptor_audit(self) -> None:
        self.write_bundle([("wickidcow/A", "A.jar", jar_bytes("AddonA", True, ["Slimefun"]))])
        with self.bundle.open("ab") as handle:
            handle.write(b"tamper")

        with self.assertRaisesRegex(ValueError, "audited bundle"):
            self.prepare()

    def test_rejects_unavailable_hard_dependency(self) -> None:
        self.write_bundle([("wickidcow/A", "A.jar", jar_bytes("AddonA", True, ["MissingPlugin"]))])

        with self.assertRaisesRegex(ValueError, "unavailable hard dependencies"):
            self.prepare()

    def test_allows_dependency_between_selected_folia_addons(self) -> None:
        self.write_bundle(
            [
                ("wickidcow/A", "A.jar", jar_bytes("AddonA", True, ["Slimefun", "AddonB"])),
                ("wickidcow/B", "B.jar", jar_bytes("AddonB", True, ["Slimefun"])),
            ]
        )

        result = self.prepare()

        self.assertEqual(result["addon_count"], 2)
        self.assertEqual(
            self.expected.read_text(encoding="utf-8"),
            "A.jar\tAddonA\nB.jar\tAddonB\n",
        )


if __name__ == "__main__":
    unittest.main()
