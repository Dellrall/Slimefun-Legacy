#!/usr/bin/env python3
"""Bind a release's exact core and bundle bytes to successful full-stack CI.

The collector must freeze the latest GitHub run/attempt, fetch complete job and
artifact metadata, verify archive digests and safe extraction, then refreeze
those identities after download. This offline verifier checks that evidence;
it neither queries GitHub nor replaces the workflow's runtime assertions.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from datetime import datetime
from pathlib import Path


REPOSITORY = 'wickidcow/Slimefun-Legacy'
WORKFLOW = '.github/workflows/paper-26.3-full-stack.yml'
BUNDLE_WORKFLOW = '.github/workflows/build-sfl-addons-compat-bundle.yml'
BUNDLE_NAME = 'SF_Addons_1.21.11-26.3.zip'
CORE_NAME = 'Slimefun-Legacy-full-stack.jar'

# Names identify the reviewed jobs, including every required runtime lane.
EXPECTED_JOBS = frozenset({
    'Resolve real Paper 26.3 API',
    'Build universal candidate against 26.3',
    'Fetch exact addon bundle under test',
    'Full stack Paper 1.21.11',
    'Full stack Paper 26.2',
    'Full stack Paper 26.3',
    'Full stack experimental Purpur 26.3 build 2646',
})
ARTIFACT_JOBS = {
    'full-stack-core': 'Build universal candidate against 26.3',
    'full-stack-addon-bundle': 'Fetch exact addon bundle under test',
    'full-stack-runtime-1.21.11': 'Full stack Paper 1.21.11',
    'full-stack-runtime-26.2': 'Full stack Paper 26.2',
    'full-stack-runtime-26.3': 'Full stack Paper 26.3',
    'full-stack-runtime-purpur-26.3': 'Full stack experimental Purpur 26.3 build 2646',
}


class FullStackEvidenceError(ValueError):
    """Missing, inconsistent or non-accepting release evidence."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FullStackEvidenceError(message)


def positive_integer(value: object) -> bool:
    return type(value) is int and value > 0


def read_file(path: Path) -> bytes:
    try:
        require(stat.S_ISREG(path.lstat().st_mode), 'Evidence must be a regular file: ' + path.name)
        return path.read_bytes()
    except OSError as error:
        raise FullStackEvidenceError('Cannot read required evidence file: ' + path.name) from error


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate JSON field in release evidence')
        value[key] = item
    return value


def read_json(path: Path) -> dict:
    try:
        value = json.loads(read_file(path), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise FullStackEvidenceError('Invalid JSON evidence: ' + path.name) from error
    require(isinstance(value, dict), 'Expected an evidence JSON object: ' + path.name)
    return value


def timestamp(value: object) -> datetime:
    require(isinstance(value, str), 'Missing evidence timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise FullStackEvidenceError('Invalid evidence timestamp') from error
    require(parsed.tzinfo is not None, 'Evidence timestamps must specify a timezone')
    return parsed


def validate_run(run: dict, workflow: str, source: str, events: set[str]) -> None:
    require(positive_integer(run.get('id')) and positive_integer(run.get('run_attempt')),
            'Missing workflow run or attempt identity')
    require(run.get('path') == workflow and isinstance(run.get('event'), str) and run['event'] in events,
            'Unexpected workflow or event; release-archive fallback is not accepted')
    require(run.get('head_sha') == source and run.get('head_branch') == 'master',
            'Workflow did not validate the exact master source')
    require(run.get('status') == 'completed' and run.get('conclusion') == 'success',
            'Workflow is not successfully completed')
    repository, head_repository = run.get('repository'), run.get('head_repository')
    require(isinstance(repository, dict) and isinstance(head_repository, dict),
            'Workflow repository identities are missing')
    require(repository.get('full_name') == head_repository.get('full_name') == REPOSITORY
            and positive_integer(repository.get('id')) and positive_integer(head_repository.get('id'))
            and repository['id'] == head_repository['id'],
            'Workflow is not from the canonical repository')


def validate_jobs(payload: dict, run: dict, source: str) -> dict[str, dict]:
    rows = payload.get('jobs')
    require(isinstance(rows, list) and type(payload.get('total_count')) is int
            and payload['total_count'] == len(rows) == len(EXPECTED_JOBS),
            'Incomplete or unexpected full-stack job set')
    jobs, identifiers = {}, set()
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get('name'), str) and row['name'] in EXPECTED_JOBS,
                'Unexpected full-stack job')
        name, identifier = row['name'], row.get('id')
        require(name not in jobs and positive_integer(identifier) and identifier not in identifiers,
                'Duplicate or invalid full-stack job identity')
        require(row.get('run_id') == run['id'] and row.get('head_sha') == source,
                'Full-stack job belongs to a different run or source')
        require(positive_integer(row.get('run_attempt')) and row['run_attempt'] <= run['run_attempt'],
                'Full-stack job attempt is inconsistent with the frozen run')
        require(row.get('status') == 'completed' and row.get('conclusion') == 'success',
                'Every required full-stack job must succeed without skips')
        require(timestamp(row.get('started_at')) <= timestamp(row.get('completed_at')),
                'Full-stack job timestamps are reversed')
        identifiers.add(identifier)
        jobs[name] = row
    require(set(jobs) == EXPECTED_JOBS, 'A required full-stack job is absent')
    require(max(row['run_attempt'] for row in rows) == run['run_attempt'],
            'Job evidence predates the frozen latest workflow attempt')
    return jobs


def validate_artifacts(payload: dict, run: dict, jobs: dict[str, dict], source: str) -> dict[str, dict]:
    rows = payload.get('artifacts')
    require(isinstance(rows, list) and type(payload.get('total_count')) is int
            and payload['total_count'] == len(rows), 'Incomplete full-stack artifact metadata')
    selected, identifiers = {}, set()
    for row in rows:
        require(isinstance(row, dict) and positive_integer(row.get('id'))
                and row['id'] not in identifiers, 'Duplicate or invalid artifact identity')
        identifiers.add(row['id'])
        name = row.get('name')
        require(isinstance(name, str), 'Missing artifact name')
        if name not in ARTIFACT_JOBS:
            continue
        require(name not in selected, 'Ambiguous required full-stack artifact')
        require(row.get('expired') is False and positive_integer(row.get('size_in_bytes'))
                and isinstance(row.get('digest'), str)
                and re.fullmatch(r'sha256:[0-9a-f]{64}', row['digest']) is not None,
                'Required artifact lacks a current byte identity')
        origin = row.get('workflow_run')
        require(isinstance(origin, dict) and origin.get('id') == run['id']
                and origin.get('head_sha') == source and origin.get('head_branch') == 'master'
                and origin.get('repository_id') == run['repository']['id']
                and origin.get('head_repository_id') == run['head_repository']['id'],
                'Artifact belongs to another workflow run, repository or source')
        producer = jobs[ARTIFACT_JOBS[name]]
        require(timestamp(producer['started_at']) <= timestamp(row.get('created_at'))
                <= timestamp(producer['completed_at']),
                'Artifact was not created by its selected successful job')
        selected[name] = row
    require(set(selected) == set(ARTIFACT_JOBS), 'A required full-stack artifact is missing')
    return selected


def exact_directory(directory: Path, names: set[str]) -> None:
    try:
        require(stat.S_ISDIR(directory.lstat().st_mode), 'Expected a regular artifact directory')
        require({path.name for path in directory.iterdir()} == names,
                'Unexpected extracted full-stack artifact membership')
    except OSError as error:
        raise FullStackEvidenceError('Missing extracted full-stack artifact directory') from error


def file_identity(data: bytes) -> dict:
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def verify_full_stack_evidence(evidence_dir: Path, core: Path, bundle: Path, expected_source: str) -> dict:
    """Reject a release unless the exact bytes passed all seven full-stack jobs."""
    require(isinstance(expected_source, str) and re.fullmatch(r'[0-9a-f]{40}', expected_source) is not None,
            'Expected a complete release source commit')
    root = evidence_dir / 'fullstack'
    run = read_json(root / 'run.json')
    bundle_run = read_json(evidence_dir / 'bundle-run.json')
    validate_run(run, WORKFLOW, expected_source, {'workflow_run'})
    validate_run(bundle_run, BUNDLE_WORKFLOW, expected_source, {'push', 'schedule', 'workflow_dispatch'})
    require(run['repository']['id'] == bundle_run['repository']['id'] and run['id'] != bundle_run['id'],
            'Full-stack and bundle workflow identities conflict')
    jobs = validate_jobs(read_json(root / 'jobs.json'), run, expected_source)
    artifacts = validate_artifacts(read_json(root / 'artifacts.json'), run, jobs, expected_source)
    exact_directory(root / 'full-stack-core', {CORE_NAME})
    exact_directory(root / 'full-stack-addon-bundle', {BUNDLE_NAME, 'bundle-source.txt'})
    tested_core = read_file(root / 'full-stack-core' / CORE_NAME)
    tested_bundle = read_file(root / 'full-stack-addon-bundle' / BUNDLE_NAME)
    require(tested_core == read_file(core) and bool(tested_core), 'Full-stack tested a different release core JAR')
    require(tested_bundle == read_file(bundle) and bool(tested_bundle), 'Full-stack tested a different release addon ZIP')
    try:
        lines = read_file(root / 'full-stack-addon-bundle' / 'bundle-source.txt').decode('utf-8').splitlines()
    except UnicodeError as error:
        raise FullStackEvidenceError('Invalid full-stack bundle provenance text') from error
    provenance = {}
    for line in lines:
        require('=' in line, 'Malformed full-stack bundle provenance')
        key, value = line.split('=', 1)
        require(key not in provenance, 'Duplicate full-stack bundle provenance field')
        provenance[key] = value
    require(provenance == {'source': 'workflow-artifact', 'run_id': str(bundle_run['id']),
                           'head_sha': expected_source},
            'Full-stack did not test the exact selected canonical bundle run')
    return {
        'schema': 1, 'status': 'PASS', 'source': expected_source,
        'scope': 'Exact-input full-stack workflow acceptance binding; no independent runtime-log inspection.',
        'fullstack_run': {'id': run['id'], 'attempt': run['run_attempt'], 'event': run['event']},
        'bundle_run': {'id': bundle_run['id'], 'attempt': bundle_run['run_attempt'], 'event': bundle_run['event']},
        'required_jobs': len(jobs), 'runtime_lanes': 4,
        'core': file_identity(tested_core), 'bundle': file_identity(tested_bundle),
        'artifacts': {name: {'id': row['id'], 'digest': row['digest'], 'size_in_bytes': row['size_in_bytes']}
                      for name, row in artifacts.items()},
    }
