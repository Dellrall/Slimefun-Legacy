#!/usr/bin/env python3
"""Isolated, nonpublishing Networks-only r139 candidate. Never changes remote refs/assets."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh_release_addon import refresh
from prepare_r137_release_candidate import gh_json, validate_release

REPO = 'wickidcow/Slimefun-Legacy'
NETWORKS = 'wickidcow/SF_NetworksExp'
NEW_COMMIT = 'c0b388e45e929c1a721d7a8aa968b2e0d4fc10e9'
NEW_HASH = '25a1bbeef780bb3d263506892df3b8b8cb42ec3be5ee5d36393c8fe1e7c52d89'
OLD_HASH = '534768b57854fdc21280bda483266217a61bc140a48df3f246c71842c82b173d'
CORE_HASH = '72a524d7c0d6f75a9decbf06679515887273ae53673d3f5ee38f355bef952c96'
BUNDLE = 'SF_Addons_1.21.11-26.3.zip'
CONFIG = {
    'release_id': 412654205, 'release_tag': 'v4.1.74',
    'core_source_commit': '4f8aa1e9c288751aeefb9a9f72dbac17a6322b5a',
    'baseline_assets': {
        BUNDLE: {'id': 642338930, 'size': 24444372, 'sha256': OLD_HASH},
        'SF_Addons_r136_1.21.11-26.3.zip': {'id': 641318435, 'size': 24440999, 'sha256': '79b9cb70a522a9ed97de3d9107d4750a913c4372043e5ee8cfeca0a1f85afc9f'},
        'Slimefun-Legacy4.1.74.jar': {'id': 640213945, 'size': 8668060, 'sha256': CORE_HASH},
        'SlimefunLegacyRP.zip': {'id': 640213951, 'size': 9143959, 'sha256': '1b856fff90fe78b7d5964a86a8ed281517d073a082db485d73f31cd07aa64a83'},
    },
    'bundle_revision': 139, 'expected_addons': 45, 'repository': NETWORKS,
    'old_bundle_sha256': OLD_HASH, 'old_jar': 'SF_Networks1.0.55.jar',
    'old_commit': 'bcdef34d362dc74aa1aab23c8961a629daa79950',
    'new_jar': 'SF_Networks1.0.56.jar', 'new_version': '1.0.56',
    'new_commit': NEW_COMMIT, 'new_sha256': NEW_HASH,
    'new_distributable_api': '1.21.11-R0.1-SNAPSHOT',
    'new_build_core_version': '4.1.74', 'new_paper_26_3_api': '26.3.build.176-stable',
    'compatibility_note': 'r139 Networks-only candidate: published Networks 1.0.56 guards failed VOID cleanup and exact item snapshots. All other 44 addon JARs, including MagicExpansion 1.1.13, remain identical to published r137. This does not repair the original source conflict. r138 is reserved for separate MagicExpansion work. No core/resource-pack or live-server change.'
}
PATCHES = {
    'compatibility/sfl-addon-release-matrix.json': '33212e506d1857614fbc67191adfc5030fbefc8c',
    'scripts/runtime/r135_fluffy_networks/run_probe.py': 'aa45d21c15c3d0141d87dad69c51bba36701aed5',
    'scripts/runtime/black_market/run_probe.py': 'c6419305c31aa8a583bf375f883964e96fde3405',
}

def require(ok, why):
    if not ok:
        raise RuntimeError(why)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def replace_once(text, old, new):
    require(text.count(old) == 1, 'Source anchor drift: ' + old[:100])
    return text.replace(old, new, 1)

def admit():
    # Patch only the disposable checkout, and refuse any concurrent source drift.
    for name, expected in PATCHES.items():
        data = Path(name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        require(actual == expected, 'Unexpected source blob: ' + name)
    path = Path('compatibility/sfl-addon-release-matrix.json')
    text = path.read_text()
    text = replace_once(text, '"bundle_revision": 137', '"bundle_revision": 139')
    text = replace_once(text, CONFIG['old_commit'], NEW_COMMIT)
    path.write_text(text)
    path = Path('scripts/runtime/r135_fluffy_networks/run_probe.py')
    text = path.read_text()
    anchor = '    137: ("SF_Networks1.0.55.jar", "bcdef34d362dc74aa1aab23c8961a629daa79950"),'
    text = replace_once(text, anchor, anchor + '\n    139: ("SF_Networks1.0.56.jar", "' + NEW_COMMIT + '"),')
    text = replace_once(text, 'requires r135, r136 or r137;', 'requires r135, r136 or r137, or explicitly pinned r139;')
    text = replace_once(text, 'version = "1.0.54" if evidence["bundle_revision"] == 135 else "1.0.55"',
                        'version = NETWORK_VERSIONS[evidence["bundle_revision"]][0].removeprefix("SF_Networks").removesuffix(".jar")')
    path.write_text(text)
    path = Path('scripts/runtime/black_market/run_probe.py')
    text = path.read_text()
    text = replace_once(text, 'manifest["bundle_revision"] != 137', 'manifest["bundle_revision"] not in (137, 139)')
    text = replace_once(text, 'This exact-source probe requires candidate r137', 'This exact-source probe requires candidate r137 or pinned Networks r139')
    anchor = '        tested = {}'
    extra = '''        if manifest["bundle_revision"] == 139:
            network = [r for r in rows if r["repository"] == "wickidcow/SF_NetworksExp"]
            if (len(network) != 1 or network[0].get("commit") != "NEW_COMMIT"
                    or network[0].get("jar") != "SF_Networks1.0.56.jar"
                    or network[0].get("sha256") != "NEW_HASH"):
                raise RuntimeError("Wrong exact Networks release for r139")
'''.replace('NEW_COMMIT', NEW_COMMIT).replace('NEW_HASH', NEW_HASH)
    text = replace_once(text, anchor, extra + anchor)
    text = replace_once(text, '"bundle_revision": 137,', '"bundle_revision": manifest["bundle_revision"],')
    path.write_text(text)
    for test in ('test_native_storage_probe_contracts.py', 'test_black_market_probe_contracts.py'):
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts', '-p', test, '-v'], check=True)
    print('Existing admission tests passed; r138/unknown revisions remain rejected. No remote source changes.')


def prepare():
    admit()
    validate_release(gh_json(f'repos/{REPO}/releases/tags/v4.1.74'), CONFIG)
    release = gh_json(f'repos/{NETWORKS}/releases/tags/v1.0.56')
    require(release['id'] == 414357261 and release['target_commitish'] == NEW_COMMIT
            and not release['draft'] and not release['prerelease'], 'Networks release changed')
    require(len(release['assets']) == 1 and release['assets'][0]['id'] == 645451428
            and release['assets'][0]['digest'] == 'sha256:' + NEW_HASH, 'Networks asset changed')
    run = gh_json(f'repos/{NETWORKS}/actions/runs/38820245987')
    require(run['head_sha'] == NEW_COMMIT and run['status'] == 'completed'
            and run['conclusion'] == 'success', 'Published Networks CI not green')
    output = Path('build/networks-r139')
    output.mkdir(parents=True, exist_ok=False)
    baseline = output / 'baseline'
    baseline.mkdir()
    for name in (BUNDLE, 'Slimefun-Legacy4.1.74.jar'):
        subprocess.run(['gh', 'release', 'download', 'v4.1.74', '--repo', REPO, '--pattern', name,
                        '--dir', str(baseline)], check=True, timeout=240)
        require(digest(baseline / name) == CONFIG['baseline_assets'][name]['sha256'], 'Baseline hash mismatch')
    subprocess.run(['gh', 'release', 'download', 'v1.0.56', '--repo', NETWORKS,
                    '--pattern', CONFIG['new_jar'], '--dir', str(output)], check=True, timeout=180)
    jar = output / CONFIG['new_jar']
    require(digest(jar) == NEW_HASH, 'Networks download hash mismatch')
    with zipfile.ZipFile(jar) as archive:
        require(not any(n.startswith(('networksprobe/', 'audit/', 'org/junit/', 'org/mockito/'))
                        for n in archive.namelist()), 'Diagnostic classes in release JAR')
    matrix = json.loads(Path('compatibility/sfl-addon-release-matrix.json').read_text())
    result = refresh(CONFIG, matrix, baseline / BUNDLE, jar, output / BUNDLE)
    refresh(CONFIG, matrix, baseline / BUNDLE, jar, output / 'repeat.zip')
    require((output / BUNDLE).read_bytes() == (output / 'repeat.zip').read_bytes(), 'Nondeterministic bundle')
    (output / 'repeat.zip').unlink()
    (output / 'Slimefun-Legacy-full-stack.jar').write_bytes((baseline / 'Slimefun-Legacy4.1.74.jar').read_bytes())
    for name in PATCHES:
        dest = output / 'source' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(name).read_bytes())
    diff = subprocess.run(['git', 'diff', '--', *PATCHES], check=True, capture_output=True).stdout
    (output / 'integration.patch').write_bytes(diff)
    (output / 'refresh-config.json').write_text(json.dumps(CONFIG, indent=2) + '\n')
    validate_release(gh_json(f'repos/{REPO}/releases/tags/v4.1.74'), CONFIG)
    result.update(state='UNPUBLISHED_NETWORKS_ONLY_CANDIDATE', published_core_sha256=CORE_HASH,
                  publication=False, deterministic_repeat=True,
                  source_changes='Disposable checkout only; master matrix is NOT updated',
                  concurrent_work='r138 MagicExpansion and PR392 core release are separate')
    (output / 'readiness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


def verify():
    candidate = Path('candidate')
    expected = digest(candidate / BUNDLE)
    ready = json.loads((candidate / 'readiness.json').read_text())
    require(ready['bundle_sha256'] == expected and ready['unchanged_addons'] == 44, 'Candidate identity drift')
    require(digest(candidate / 'Slimefun-Legacy-full-stack.jar') == CORE_HASH, 'Core drift')
    lanes = {}
    for lane in ('1.21.11', '26.2', '26.3', 'purpur-26.3'):
        reports = list((Path('evidence') / ('networks-r139-native-' + lane)).rglob('black-market-result.json'))
        require(len(reports) == 1, 'Missing lane evidence: ' + lane)
        path = reports[0]
        report = json.loads(path.read_text())
        require(report['result'] == 'PASS' and report['bundle_revision'] == 139
                and report['bundle_sha256'] == expected and report['core_sha256'] == CORE_HASH, 'Wrong native bytes')
        require(report['tested_addons'][NETWORKS]['sha256'] == NEW_HASH, 'Wrong native Networks')
        require([p['phase'] for p in report['phases']] == ['seed', 'verify', 'missing', 'restored'], 'Missing phase')
        for phase in report['phases']:
            require(phase['result'] == 'PASS' and phase['exit_code'] == 0 and phase['assertions'] >= 10, 'Failed native phase')
            require(digest(path.parent / ('black-market-' + phase['phase'] + '.console.log')) == phase['console_sha256'], 'Log mismatch')
        if lane == '26.3':
            native = json.loads((path.parent / 'native-r135-result.json').read_text())
            require(native['result'] == 'PASS' and native['process_exit_code'] == 0
                    and native['core_jar_sha256'] == CORE_HASH
                    and native['tested_addons'][NETWORKS]['sha256'] == NEW_HASH, 'Storage conservation failed')
        lanes[lane] = report
    # Do not overwrite a concurrent publication with an older selection.
    validate_release(gh_json(f'repos/{REPO}/releases/tags/v4.1.74'), CONFIG)
    result = {'gate': 'PASS', 'publication': 'NOT_PUBLISHED', 'run_id': os.environ['GITHUB_RUN_ID'],
              'candidate': ready, 'lanes': lanes, 'limitations': 'Synthetic restart/storage checks, not live-world repair. Canonical source-pin integration remains pending.'}
    Path('networks-r139-ready.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: exact published-core candidate, all four runtime lanes and unchanged release assets')

if __name__ == '__main__':
    require(len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'admit', 'verify'), 'Expected prepare/admit/verify')
    {'prepare': prepare, 'admit': admit, 'verify': verify}[sys.argv[1]]()
