"""Release contract: Slimefun Legacy must not handle Geyser/Bedrock assets."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/reproducible-release.yml"


class JavaOnlyReleaseScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_no_external_platform_pack_handlers(self):
        self.assertNotRegex(self.text.lower(), r"bedrock|geyser")
        self.assertNotIn("--clobber", self.text)

    def test_three_java_release_assets_only(self):
        self.assertIn('gh release create "$TAG" "$JAR" "$BUNDLE" "$RESOURCE_PACK"', self.text)
        self.assertIn('if [[ "$ASSET_COUNT" -ne 3 ]]; then', self.text)
        self.assertIn('Canonical addon bundle', self.text)

    def test_publish_requires_current_source_and_native_evidence(self):
        self.assertIn('steps.runtime_evidence.outcome == \'success\'', self.text)
        self.assertIn('require_complete native-entity-retirement.yml push', self.text)
        self.assertIn('require_complete paper-26.3-full-stack.yml workflow_run', self.text)
        self.assertIn('test "$GITHUB_SHA" = "$(gh api', self.text)

    def test_published_bytes_are_verified_and_prior_release_unchanged(self):
        self.assertIn('gh release download "$TAG"', self.text)
        self.assertIn('Published Java release digest mismatch', self.text)
        self.assertIn('Published Java release bytes changed', self.text)
        self.assertIn('Release $TAG already exists at identical source', self.text)
        self.assertIn('if [[ "$ASSET_COUNT" -ne 3 ]]; then', self.text)
        self.assertNotIn('OPTIONAL_', self.text)
        java_pack_gate = (ROOT / 'scripts/verify_release_resource_pack.py').read_text(encoding='utf-8')
        self.assertIn('release layout requires three Java assets', java_pack_gate)
        self.assertIn('if [[ "$ASSET_COUNT" -ne 3 ]]', java_pack_gate)


if __name__ == "__main__":
    unittest.main()
