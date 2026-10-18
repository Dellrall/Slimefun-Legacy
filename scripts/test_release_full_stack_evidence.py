#!/usr/bin/env python3
"""Offline regression fixtures for exact-input release/full-stack acceptance."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_release_full_stack_evidence import (
    BUNDLE_NAME, BUNDLE_WORKFLOW, CORE_NAME,
    FullStackEvidenceError, WORKFLOW, verify_full_stack_evidence,
)


class FullStackReleaseEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fullstack = self.root / 'fullstack'
        self.fullstack.mkdir()
        self.source = '1' * 40
        self.repository = {'id': 1000, 'full_name': 'wickidcow/Slimefun-Legacy'}
        self.run = {
            'id': 200, 'run_attempt': 1, 'event': 'workflow_run', 'path': WORKFLOW,
            'head_sha': self.source, 'head_branch': 'master',
            'repository': dict(self.repository), 'head_repository': dict(self.repository),
            'status': 'completed', 'conclusion': 'success',
        }
        self.bundle_run = dict(copy.deepcopy(self.run), id=100, event='schedule', path=BUNDLE_WORKFLOW)
        # These identities are the observed workflow contract, independent of verifier constants.
        job_names = [
            'Resolve real Paper 26.3 API', 'Build universal candidate against 26.3',
            'Fetch exact addon bundle under test', 'Full stack Paper 1.21.11',
            'Full stack Paper 26.2', 'Full stack Paper 26.3',
            'Full stack experimental Purpur 26.3 build 2646',
        ]
        artifact_names = [
            'full-stack-core', 'full-stack-addon-bundle', 'full-stack-runtime-1.21.11',
            'full-stack-runtime-26.2', 'full-stack-runtime-26.3', 'full-stack-runtime-purpur-26.3',
        ]
        self.jobs = [
            {'id': 300 + index, 'run_id': 200, 'run_attempt': 1, 'head_sha': self.source,
             'name': name, 'status': 'completed', 'conclusion': 'success',
             'started_at': '2026-10-18T11:08:00Z', 'completed_at': '2026-10-18T11:10:00Z'}
            for index, name in enumerate(job_names)
        ]
        self.artifacts = [
            {'id': 400 + index, 'name': name, 'size_in_bytes': 128, 'digest': 'sha256:' + 'a' * 64,
             'expired': False, 'created_at': '2026-10-18T11:09:00Z',
             'workflow_run': {'id': 200, 'repository_id': 1000, 'head_repository_id': 1000,
                              'head_sha': self.source, 'head_branch': 'master'}}
            for index, name in enumerate(artifact_names)
        ]
        # This layer compares exact bytes; the build/native layers validate JAR/ZIP contents.
        self.core = self.root / 'release-core.jar'
        self.bundle = self.root / BUNDLE_NAME
        self.core.write_bytes(b'non-executable core identity fixture')
        self.bundle.write_bytes(b'non-executable bundle identity fixture')
        self.core_dir = self.fullstack / 'full-stack-core'
        self.bundle_dir = self.fullstack / 'full-stack-addon-bundle'
        self.core_dir.mkdir()
        self.bundle_dir.mkdir()
        (self.core_dir / CORE_NAME).write_bytes(self.core.read_bytes())
        (self.bundle_dir / BUNDLE_NAME).write_bytes(self.bundle.read_bytes())
        self.provenance = self.bundle_dir / 'bundle-source.txt'
        self.provenance.write_text('source=workflow-artifact\nrun_id=100\nhead_sha=' + self.source + '\n')
        self.write_metadata()

    def write_metadata(self):
        for path, data in [
            (self.fullstack / 'run.json', self.run),
            (self.root / 'bundle-run.json', self.bundle_run),
            (self.fullstack / 'jobs.json', {'total_count': len(self.jobs), 'jobs': self.jobs}),
            (self.fullstack / 'artifacts.json', {'total_count': len(self.artifacts), 'artifacts': self.artifacts}),
        ]:
            path.write_text(json.dumps(data), encoding='utf-8')

    def verify(self):
        return verify_full_stack_evidence(self.root, self.core, self.bundle, self.source)

    def test_exact_accepted_input_bytes_and_all_seven_jobs_pass_without_writes(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report = self.verify()
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual('PASS', report['status'])
        self.assertEqual(7, report['required_jobs'])
        self.assertEqual(4, report['runtime_lanes'])
        self.assertEqual(hashlib.sha256(self.bundle.read_bytes()).hexdigest(), report['bundle']['sha256'])
        self.assertEqual(100, report['bundle_run']['id'])

    def test_successful_retained_jobs_from_an_earlier_attempt_remain_valid(self):
        self.run['run_attempt'] = 2
        self.jobs[-1]['run_attempt'] = 2
        self.write_metadata()
        self.assertEqual(2, self.verify()['fullstack_run']['attempt'])

    def test_wholly_stale_or_future_attempt_job_evidence_is_rejected(self):
        self.run['run_attempt'] = 2
        self.write_metadata()
        with self.assertRaisesRegex(FullStackEvidenceError, 'predates'):
            self.verify()
        self.jobs[-1]['run_attempt'] = 3
        self.write_metadata()
        with self.assertRaisesRegex(FullStackEvidenceError, 'attempt'):
            self.verify()

    def test_same_head_manual_scheduled_push_or_pr_fullstack_is_not_release_acceptance(self):
        for event in ('workflow_dispatch', 'schedule', 'push', 'pull_request', ['workflow_run'], None):
            with self.subTest(event=event):
                self.run['event'] = event
                self.write_metadata()
                with self.assertRaisesRegex(FullStackEvidenceError, 'event'):
                    self.verify()

    def test_wrong_workflow_head_branch_or_repository_is_rejected(self):
        baseline = copy.deepcopy(self.run)
        changes = [
            ('path', BUNDLE_WORKFLOW), ('head_sha', '2' * 40), ('head_branch', 'candidate'),
            ('repository', {'id': 1000, 'full_name': 'other/Slimefun-Legacy'}),
            ('head_repository', {'id': 2000, 'full_name': 'wickidcow/Slimefun-Legacy'}),
        ]
        for key, value in changes:
            with self.subTest(field=key):
                self.run = dict(copy.deepcopy(baseline), **{key: value})
                self.write_metadata()
                with self.assertRaises(FullStackEvidenceError):
                    self.verify()

    def test_incomplete_or_failed_workflow_cannot_use_green_job_metadata(self):
        for target in (self.run, self.bundle_run):
            for key, value in [('status', 'in_progress'), ('conclusion', 'failure')]:
                with self.subTest(target=target['id'], field=key):
                    old = target[key]
                    target[key] = value
                    self.write_metadata()
                    with self.assertRaisesRegex(FullStackEvidenceError, 'successfully completed'):
                        self.verify()
                    target[key] = old

    def test_selected_bundle_run_must_be_canonical_exact_master_source(self):
        baseline = copy.deepcopy(self.bundle_run)
        for key, value in [('head_sha', '2' * 40), ('path', WORKFLOW), ('event', 'pull_request')]:
            with self.subTest(field=key):
                self.bundle_run = dict(copy.deepcopy(baseline), **{key: value})
                self.write_metadata()
                with self.assertRaises(FullStackEvidenceError):
                    self.verify()

    def test_same_filename_and_source_label_cannot_hide_different_core_bytes(self):
        self.core.write_bytes(self.core.read_bytes() + b' changed')
        with self.assertRaisesRegex(FullStackEvidenceError, 'different release core'):
            self.verify()

    def test_same_source_cannot_hide_different_bundle_container_bytes(self):
        self.bundle.write_bytes(self.bundle.read_bytes() + b' changed packaging timestamps')
        with self.assertRaisesRegex(FullStackEvidenceError, 'different release addon ZIP'):
            self.verify()

    def test_bundle_provenance_rejects_public_fallback_wrong_run_head_and_ambiguity(self):
        valid = self.provenance.read_text()
        invalid = [
            valid.replace('workflow-artifact', 'release'), valid.replace('run_id=100', 'run_id=99'),
            valid.replace(self.source, '2' * 40), valid + 'run_id=100\n',
            valid + 'release_tag=v4.1.75\n', valid.replace('run_id=100\n', ''),
        ]
        for value in invalid:
            with self.subTest(value=value.splitlines()[0]):
                self.provenance.write_text(value)
                with self.assertRaises(FullStackEvidenceError):
                    self.verify()

    def test_any_skipped_failed_or_cancelled_required_job_blocks_release(self):
        for conclusion in ('skipped', 'failure', 'cancelled', 'neutral', None):
            with self.subTest(conclusion=conclusion):
                self.jobs[-1]['conclusion'] = conclusion
                self.write_metadata()
                with self.assertRaisesRegex(FullStackEvidenceError, 'without skips'):
                    self.verify()

    def test_missing_duplicate_or_unexpected_job_cannot_replace_a_runtime_lane(self):
        original = copy.deepcopy(self.jobs)
        variants = [original[:-1], original[:-1] + [copy.deepcopy(original[0])],
                    original[:-1] + [dict(original[-1], name='Unknown job')]]
        for rows in variants:
            with self.subTest(count=len(rows)):
                self.jobs = rows
                self.write_metadata()
                with self.assertRaises(FullStackEvidenceError):
                    self.verify()

    def test_job_run_and_head_must_match_the_selected_workflow(self):
        for field, value in [('run_id', 201), ('head_sha', '2' * 40), ('run_attempt', False)]:
            with self.subTest(field=field):
                original = self.jobs[-1][field]
                self.jobs[-1][field] = value
                self.write_metadata()
                with self.assertRaises(FullStackEvidenceError):
                    self.verify()
                self.jobs[-1][field] = original

    def test_incomplete_api_pagination_is_rejected(self):
        for name, field, rows in [('jobs', 'jobs', self.jobs), ('artifacts', 'artifacts', self.artifacts)]:
            with self.subTest(collection=name):
                self.write_metadata()
                (self.fullstack / (name + '.json')).write_text(json.dumps({'total_count': len(rows) + 1, field: rows}))
                with self.assertRaisesRegex(FullStackEvidenceError, 'Incomplete'):
                    self.verify()

    def test_all_four_runtime_artifact_identities_are_required(self):
        self.artifacts.pop()
        self.write_metadata()
        with self.assertRaisesRegex(FullStackEvidenceError, 'artifact is missing'):
            self.verify()

    def test_duplicate_or_expired_required_artifact_is_rejected(self):
        original = copy.deepcopy(self.artifacts)
        self.artifacts.append(dict(self.artifacts[-1], id=999))
        self.write_metadata()
        with self.assertRaisesRegex(FullStackEvidenceError, 'Ambiguous'):
            self.verify()
        self.artifacts = original
        self.artifacts[-1]['expired'] = True
        self.write_metadata()
        with self.assertRaisesRegex(FullStackEvidenceError, 'current byte identity'):
            self.verify()

    def test_artifact_digest_source_and_run_are_checked(self):
        original = copy.deepcopy(self.artifacts[-1])
        for field, value in [('id', 0), ('digest', None), ('digest', 'sha256:bad'), ('size_in_bytes', 0)]:
            with self.subTest(field=field, value=value):
                self.artifacts[-1] = dict(copy.deepcopy(original), **{field: value})
                self.write_metadata()
                with self.assertRaises(FullStackEvidenceError):
                    self.verify()
        for field, value in [('id', 199), ('head_sha', '2' * 40), ('repository_id', 1001)]:
            with self.subTest(origin_field=field):
                self.artifacts[-1] = copy.deepcopy(original)
                self.artifacts[-1]['workflow_run'][field] = value
                self.write_metadata()
                with self.assertRaisesRegex(FullStackEvidenceError, 'another workflow'):
                    self.verify()

    def test_artifact_must_be_created_during_its_selected_successful_producer_job(self):
        for created_at in ('2026-10-18T11:07:59Z', '2026-10-18T11:10:01Z', '2026-10-18T11:09:00', None):
            with self.subTest(created_at=created_at):
                self.artifacts[-1]['created_at'] = created_at
                self.write_metadata()
                with self.assertRaises(FullStackEvidenceError):
                    self.verify()

    def test_unrelated_unique_artifact_metadata_is_not_a_required_lane(self):
        self.artifacts.append({'id': 999, 'name': 'additional-audit'})
        self.write_metadata()
        self.assertEqual(6, len(self.verify()['artifacts']))

    def test_extra_extracted_core_file_or_symlink_is_rejected(self):
        extra = self.core_dir / 'unselected.jar'
        extra.write_bytes(b'unselected')
        with self.assertRaisesRegex(FullStackEvidenceError, 'membership'):
            self.verify()
        extra.unlink()
        target = self.core_dir / CORE_NAME
        target.unlink()
        target.symlink_to(self.core)
        with self.assertRaisesRegex(FullStackEvidenceError, 'regular file'):
            self.verify()

    def test_missing_malformed_or_duplicate_field_metadata_fails_closed(self):
        path = self.fullstack / 'run.json'
        path.unlink()
        with self.assertRaises(FullStackEvidenceError):
            self.verify()
        for content in ('not-json', '[]', '{"id":200,"id":201}'):
            with self.subTest(content=content):
                path.write_text(content)
                with self.assertRaises(FullStackEvidenceError):
                    self.verify()


if __name__ == '__main__':
    unittest.main()
