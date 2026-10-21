#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import audit_folia_addon_admission as audit
import prepare_folia_addon_runtime as runtime
import verify_folia_addon_runtime as verification


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

    def prepare_pair(self) -> dict:
        self.write_bundle(
            [
                ("wickidcow/A", "A.jar", jar_bytes("AddonA", True, ["Slimefun"])),
                ("wickidcow/B", "B.jar", jar_bytes("AddonB", True, ["Slimefun"])),
            ]
        )
        return self.prepare()

    def verify_downloaded(self) -> dict:
        selection = verification.verified_selection(self.selection, self.expected, SOURCE)
        return verification.verify_jars(selection, self.output)

    def test_downloaded_selection_binds_exact_pairs_and_bytes(self) -> None:
        prepared = self.prepare_pair()
        receipt = self.verify_downloaded()
        self.assertEqual(receipt["addons"], prepared["addons"])
        self.assertEqual(receipt["addon_count"], 2)

    def test_rejects_duplicate_expected_rows_that_hide_an_addon(self) -> None:
        self.prepare_pair()
        self.expected.write_text("A.jar\tAddonA\nA.jar\tAddonA\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JAR/plugin"):
            self.verify_downloaded()

    def test_rejects_reassigned_plugin_names_with_unchanged_row_count(self) -> None:
        self.prepare_pair()
        self.expected.write_text("A.jar\tAddonB\nB.jar\tAddonA\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "pairs differ"):
            self.verify_downloaded()

    def test_rejects_selection_for_a_different_core_checkout(self) -> None:
        self.prepare_pair()
        with self.assertRaisesRegex(ValueError, "different core checkout"):
            verification.verified_selection(self.selection, self.expected, "b" * 40)

    def test_rejects_duplicate_selection_rows(self) -> None:
        prepared = self.prepare_pair()
        prepared["addons"][1] = prepared["addons"][0]
        self.selection.write_text(json.dumps(prepared), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JAR/plugin"):
            self.verify_downloaded()

    def test_rejects_missing_extra_or_changed_downloaded_jars(self) -> None:
        for mutation in ("missing", "extra", "changed"):
            with self.subTest(mutation=mutation):
                self.prepare_pair()
                if mutation == "missing":
                    (self.output / "B.jar").unlink()
                elif mutation == "extra":
                    (self.output / "Unselected.jar").write_bytes(b"unselected")
                else:
                    (self.output / "B.jar").write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "JAR set differs|digest mismatch"):
                    self.verify_downloaded()

    def test_installed_receipt_binds_core_and_exact_addon_set(self) -> None:
        prepared = self.prepare_pair()
        installed = self.root / "plugins"
        shutil.copytree(self.output, installed)
        core = self.root / "core.jar"
        core.write_bytes(b"exact-core-candidate")
        shutil.copyfile(core, installed / verification.CORE_JAR_NAME)

        receipt = verification.verify_jars(prepared, installed, core)

        self.assertEqual(receipt["core_jar_sha256"], hashlib.sha256(core.read_bytes()).hexdigest())
        self.assertEqual(receipt["addon_count"], 2)
        self.assertEqual(receipt["core_source_commit"], SOURCE)

    def test_installed_verification_rejects_changed_core_and_addon_set(self) -> None:
        prepared = self.prepare_pair()
        core = self.root / "core.jar"
        core.write_bytes(b"exact-core-candidate")
        for mutation in ("core", "addon", "missing", "extra"):
            with self.subTest(mutation=mutation):
                installed = self.root / mutation
                shutil.copytree(self.output, installed)
                shutil.copyfile(core, installed / verification.CORE_JAR_NAME)
                if mutation == "core":
                    (installed / verification.CORE_JAR_NAME).write_bytes(b"other-core")
                elif mutation == "addon":
                    (installed / "A.jar").write_bytes(b"other-addon")
                elif mutation == "missing":
                    (installed / "B.jar").unlink()
                else:
                    (installed / "Unexpected.jar").write_bytes(b"other-addon")
                with self.assertRaisesRegex(ValueError, "JAR bytes differ|digest mismatch|JAR set differs"):
                    verification.verify_jars(prepared, installed, core)


if __name__ == "__main__":
    unittest.main()
