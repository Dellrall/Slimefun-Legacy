#!/usr/bin/env python3
"""Reject source, binary and support-identity drift before canonical staging."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.stage_published_pair import stage


class PublishedPairTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.jar"
        self.output = self.root / "staged" / "Networks.jar"
        self.pin = {"repository": "wickidcow/SF_NetworksExp", "source": "a" * 40,
                    "plugin": "Networks", "version": "1.0.60", "jar": "build/libs/SF_Networks1.0.60.jar"}
        self.descriptor = "name: Networks\nversion: 1.0.60\napi-version: '1.21'\n"
        self.write_jar()

    def write_jar(self, descriptor=None, major=65):
        with zipfile.ZipFile(self.source, "w") as archive:
            archive.writestr("plugin.yml", descriptor or self.descriptor)
            archive.writestr("example/Main.class", b"\xca\xfe\xba\xbe\0\0" + major.to_bytes(2, "big"))
        self.pin["published_artifact"] = {
            "url": "https://github.com/wickidcow/SF_NetworksExp/releases/download/v1.0.60/SF_Networks1.0.60.jar",
            "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "bytes": self.source.stat().st_size,
        }

    def stage(self, **kwargs):
        return stage(kwargs.get("pin", self.pin), kwargs.get("source", self.pin["source"]),
                     kwargs.get("repository", self.pin["repository"]), self.output, local=self.source)

    def test_stages_identical_bytes_and_records_exact_published_identity(self):
        result = self.stage()
        self.assertEqual(self.source.read_bytes(), self.output.read_bytes())
        for key in ("bytes", "sha256", "url"):
            self.assertEqual(self.pin["published_artifact"][key], result[key])
        self.assertEqual(self.pin["source"], result["source"])

    def test_different_source_is_rejected_before_output(self):
        with self.assertRaisesRegex(RuntimeError, "Selected source"):
            self.stage(source="b" * 40)
        self.assertFalse(self.output.exists())

    def test_different_repository_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Selected source"):
            self.stage(repository="example/SF_NetworksExp")

    def test_unreviewed_release_url_is_rejected(self):
        self.pin["published_artifact"]["url"] = self.pin["published_artifact"]["url"].replace("v1.0.60", "latest")
        with self.assertRaisesRegex(RuntimeError, "artifact pin"):
            self.stage()

    def test_same_version_different_bytes_or_size_are_rejected(self):
        for key, value in (("sha256", "f" * 64), ("bytes", 1)):
            with self.subTest(key=key):
                pin = copy.deepcopy(self.pin)
                pin["published_artifact"][key] = value
                with self.assertRaisesRegex(RuntimeError, "size or SHA-256"):
                    self.stage(pin=pin)
                self.assertFalse(self.output.exists())

    def test_wrong_plugin_identity_is_rejected_even_with_a_matching_hash(self):
        self.write_jar(self.descriptor.replace("Networks", "Other"))
        with self.assertRaisesRegex(RuntimeError, "descriptor mismatch"):
            self.stage()

    def test_newer_api_probe_cannot_become_the_distributable(self):
        self.write_jar(self.descriptor.replace("1.21", "26.3"))
        with self.assertRaisesRegex(RuntimeError, "API floor"):
            self.stage()

    def test_newer_bytecode_cannot_become_the_distributable(self):
        self.write_jar(major=69)
        with self.assertRaisesRegex(RuntimeError, "Non-universal Java"):
            self.stage()

    def test_unaccepted_folia_declaration_is_rejected(self):
        self.write_jar(self.descriptor + "folia-supported: true\n")
        with self.assertRaisesRegex(RuntimeError, "no Folia runtime"):
            self.stage()

    def test_existing_output_and_symlink_are_preserved(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"original")
        with self.assertRaisesRegex(RuntimeError, "existing or symlinked"):
            self.stage()
        self.assertEqual(b"original", self.output.read_bytes())
        self.output.unlink()
        self.output.symlink_to(self.source)
        with self.assertRaisesRegex(RuntimeError, "existing or symlinked"):
            self.stage()
        self.assertTrue(self.output.is_symlink())


if __name__ == "__main__":
    unittest.main()
