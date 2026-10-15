"""Offline policy tests; actual pinned JARs still require the network/runtime gate."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_worldedit_runtime as helper


class ReviewedWorldEditPinsTest(unittest.TestCase):
    def report(self, minecraft):
        version, checksum = helper.REVIEWED_RUNTIME_PINS[minecraft]
        return {'version_id': version, 'sha256': checksum}

    def invoke(self, minecraft, mode=(), report=None, requested=None, error=None, allow=False):
        argv = ['prepare_worldedit_runtime.py', '--minecraft', minecraft, '--output', 'disposable']
        argv.extend(mode)
        if requested is not None:
            argv.extend(['--version-id', requested])
        if allow:
            argv.append('--allow-prerelease')
        name = 'verify_staged' if mode == ('--check-staged',) else (
            'verify_boot_log' if mode else 'stage')
        with patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()), \
                patch.object(helper, name, return_value=report or self.report(minecraft), side_effect=error) as work:
            if error is not None:
                with self.assertRaises(SystemExit) as failure:
                    helper.main()
                self.assertEqual(1, failure.exception.code)
            else:
                self.assertEqual(0, helper.main())
            return work.call_args, work.call_count

    def test_all_cli_lanes_stage_the_reviewed_identity_and_digest(self):
        for minecraft, (version, digest) in helper.REVIEWED_RUNTIME_PINS.items():
            with self.subTest(minecraft=minecraft):
                call, count = self.invoke(minecraft, allow=minecraft == '26.3')
                self.assertEqual(1, count)
                self.assertEqual((Path('disposable'), minecraft, minecraft == '26.3', version), call.args)
                self.assertEqual({'expected_sha256': digest}, call.kwargs)

    def test_revalidation_and_boot_log_modes_keep_the_same_pin(self):
        for minecraft in helper.REVIEWED_RUNTIME_PINS:
            for mode in (('--check-staged',), ('--verify-log', 'boot.log')):
                with self.subTest(minecraft=minecraft, mode=mode):
                    call, count = self.invoke(minecraft, mode=mode, allow=minecraft == '26.3')
                    self.assertEqual(1, count)
                    self.assertEqual(Path('disposable'), call.args[0])
                    self.assertEqual(minecraft, call.args[1])
                    self.assertEqual(minecraft == '26.3', call.args[-1])

    def test_default_checks_reject_a_different_digest_in_every_mode(self):
        for mode in ((), ('--check-staged',), ('--verify-log', 'boot.log')):
            for field in ('version_id', 'sha256'):
                report = self.report('26.2')
                report[field] = 'changed'
                with self.subTest(mode=mode, field=field), self.assertRaises(SystemExit) as failure:
                    self.invoke('26.2', mode=mode, report=report)
                self.assertEqual(1, failure.exception.code)

    def test_explicit_known_pin_still_requires_the_reviewed_digest(self):
        minecraft = '26.2'
        version, digest = helper.REVIEWED_RUNTIME_PINS[minecraft]
        call, _ = self.invoke(minecraft, requested=version)
        self.assertEqual({'expected_sha256': digest}, call.kwargs)
        with self.assertRaises(SystemExit) as failure:
            self.invoke(minecraft, requested=version, report={'version_id': version, 'sha256': '0' * 64})
        self.assertEqual(1, failure.exception.code)

    def test_an_explicit_other_identity_is_not_silently_replaced(self):
        report = {'version_id': 'ReviewedOverride1', 'sha256': 'f' * 64}
        call, _ = self.invoke('26.2', requested=report['version_id'], report=report)
        self.assertEqual('ReviewedOverride1', call.args[3])
        self.assertEqual({'expected_sha256': None}, call.kwargs)
        with self.assertRaises(SystemExit) as failure:
            self.invoke('26.2', requested='ReviewedOverride1')
        self.assertEqual(1, failure.exception.code)

    def test_download_failures_are_not_fallback_authorization(self):
        _, count = self.invoke('26.2', error=OSError('simulated unavailable official download'))
        self.assertEqual(1, count)

    def test_cli_never_grants_prerelease_permission_implicitly(self):
        call, count = self.invoke('26.3', error=ValueError('prerelease was not permitted'))
        self.assertEqual(1, count)
        self.assertFalse(call.args[2])

    def staged_fixture(self, expected, should_succeed):
        payload = b'fixture payload already accepted by the separate artifact validator'
        digest = hashlib.sha256(payload).hexdigest()
        version = {'id': 'Fixture1', 'version_number': 'fixture', 'version_type': 'release',
                   'date_published': '2026-01-01T00:00:00Z', 'game_versions': ['26.2'], 'loaders': ['paper']}
        file = {'url': 'https://cdn.modrinth.com/fixture.jar', 'filename': 'worldedit-bukkit-fixture.jar'}
        project = {'slug': 'worldedit', 'source_url': helper.SOURCE_REPOSITORY, 'id': '1u6JkXh5'}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(helper, 'request_bytes', return_value=b'{}'), \
                patch.object(helper, 'object_json', side_effect=[project, []]), \
                patch.object(helper, 'select_compatible_artifact',
                             return_value=(version, file, payload, {'sha256': digest})):
            output = Path(directory) / 'plugins'
            checksum = digest if expected == 'matching' else expected
            if should_succeed:
                helper.stage(output, '26.2', version_id='Fixture1', expected_sha256=checksum)
                self.assertEqual(payload, (output / 'WorldEdit-runtime.jar').read_bytes())
                self.assertTrue((output / 'worldedit-runtime.json').is_file())
            else:
                with self.assertRaisesRegex(ValueError, 'reviewed SHA-256'):
                    helper.stage(output, '26.2', version_id='Fixture1', expected_sha256=checksum)
                self.assertFalse((output / 'WorldEdit-runtime.jar').exists())
                self.assertFalse((output / 'worldedit-runtime.json').exists())
                self.assertFalse(list(output.glob('*.part')))

    def test_pinned_digest_rejection_happens_before_publishing_files(self):
        self.staged_fixture('0' * 64, False)

    def test_invalid_expected_digest_is_rejected(self):
        self.staged_fixture('not-a-digest', False)

    def test_matching_pinned_payload_is_published(self):
        self.staged_fixture('matching', True)

    def test_existing_explicit_library_selection_without_a_pin_is_preserved(self):
        self.staged_fixture(None, True)


if __name__ == '__main__':
    unittest.main()
