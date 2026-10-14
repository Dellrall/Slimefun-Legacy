import copy
import unittest
from unittest.mock import patch
from publish_r136 import CORE, HASHES, TAG, ZIP, UPDATES, green, lease

class ReleaseLeaseTest(unittest.TestCase):
    def setUp(self):
        self.release = dict(tag_name=TAG, target_commitish=CORE, draft=False, prerelease=False,
                            assets=[dict(id=i, name=n, digest='sha256:' + h)
                                    for i, (n, h) in enumerate(HASHES.items(), 1)])
        self.ids = {a['name']: a['id'] for a in self.release['assets']}

    def test_original_lease_matches_all_three_assets(self):
        self.assertEqual(set(HASHES), set(lease(self.release, HASHES, self.ids)))

    def test_changed_digest_or_asset_id_is_rejected(self):
        for field, value in [('digest', 'sha256:' + '0' * 64), ('id', 999)]:
            with self.subTest(field=field):
                altered = copy.deepcopy(self.release)
                altered['assets'][0][field] = value
                with self.assertRaises(RuntimeError):
                    lease(altered, HASHES, self.ids)

    def test_core_tag_or_release_state_must_not_change(self):
        for field, value in [('target_commitish', '0' * 40), ('tag_name', 'v4.1.75'),
                             ('draft', True), ('prerelease', True)]:
            with self.subTest(field=field):
                altered = {**self.release, field: value}
                with self.assertRaises(RuntimeError):
                    lease(altered, HASHES)

    def test_unknown_or_duplicate_assets_abort(self):
        for asset in [dict(id=9, name='unknown.jar', digest='sha256:' + 'a' * 64),
                      self.release['assets'][0]]:
            altered = copy.deepcopy(self.release)
            altered['assets'].append(asset)
            with self.assertRaises(RuntimeError):
                lease(altered, HASHES)

    def test_only_explicit_temporary_name_is_allowed(self):
        temporary = ZIP + '.r136-pending'
        self.release['assets'].append(dict(id=9, name=temporary, digest='sha256:' + 'a' * 64))
        with self.assertRaises(RuntimeError):
            lease(self.release, HASHES)
        self.assertIn(temporary, lease(self.release, HASHES, self.ids, (temporary,)))

    def test_exactly_two_expected_addons_are_selected(self):
        self.assertEqual({'wickidcow/SF_NetworksExp', 'wickidcow/SF_MagicExpansion'},
                         {u['repository'] for u in UPDATES})
        self.assertEqual(['1.0.55', '1.1.12'], [u['version'] for u in UPDATES])

    def test_ci_must_be_completed_success_at_exact_head(self):
        for state in [dict(head_sha='wrong', status='completed', conclusion='success'),
                      dict(head_sha='head', status='in_progress', conclusion=None),
                      dict(head_sha='head', status='completed', conclusion='skipped')]:
            with patch('publish_r136.api', return_value=state), self.assertRaises(RuntimeError):
                green('owner/repo', 1, 'head')
        with patch('publish_r136.api', return_value=dict(
                head_sha='head', status='completed', conclusion='success')):
            green('owner/repo', 1, 'head')

if __name__ == '__main__':
    unittest.main()
