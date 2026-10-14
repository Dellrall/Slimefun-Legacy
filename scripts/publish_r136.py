#!/usr/bin/env python3
"""Publish only the approved r136 addon ZIP; retain the released core and RP."""
from __future__ import annotations
import copy
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = 'wickidcow/Slimefun-Legacy'
TAG = 'v4.1.74'
CORE = '4f8aa1e9c288751aeefb9a9f72dbac17a6322b5a'
TESTED = '4cfd8f5362151f1189f984fe10ff2973c9cd2696'
ZIP = 'SF_Addons_1.21.11-26.3.zip'
HASHES = {
    ZIP: 'dd0f8e3dc952acbd2dcf78f1bc85a5c1592b6ef2adf0d0c9af88fb45a40078f1',
    'Slimefun-Legacy4.1.74.jar': '72a524d7c0d6f75a9decbf06679515887273ae53673d3f5ee38f355bef952c96',
    'SlimefunLegacyRP.zip': '1b856fff90fe78b7d5964a86a8ed281517d073a082db485d73f31cd07aa64a83',
}
UPDATES = [
    dict(repository='wickidcow/SF_NetworksExp', slug='networksexp', version='1.0.55',
         old_jar='SF_Networks1.0.54.jar', new_jar='SF_Networks1.0.55.jar',
         old_commit='c24064cbeafe4f112c7d46bf3de5617fa151d88d',
         source='bcdef34d362dc74aa1aab23c8961a629daa79950',
         release_source='56b447a535502c0f82bc94e0d734e8d4aad85f9f',
         run=38561167615, core='4.1.74', paper='26.3.build.176-stable'),
    dict(repository='wickidcow/SF_MagicExpansion', slug='magicexpansion', version='1.1.12',
         old_jar='SF_MagicExpansion1.1.11.jar', new_jar='SF_MagicExpansion1.1.12.jar',
         old_commit='8fbd796bd139829c1df8aacd24e50497f06bad20',
         source='144d973a014ce943e4e9173ea17f7bf31ed00fa3',
         release_source='7a33360bf19a1a82e7874025f6e8f196938b3c7b',
         run=38598789759, core='4.1.61', paper='26.3-rc-3.build.1-alpha'),
]

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def command(*args):
    return subprocess.check_output(args, text=True, timeout=360)

def api(path, *args):
    result = command('gh', 'api', path, *args)
    return json.loads(result) if result.strip() else None

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def lease(release, expected, ids=None, extra=()):
    require(release['tag_name'] == TAG and release['target_commitish'] == CORE,
            'Release tag/core identity changed')
    require(not release['draft'] and not release['prerelease'], 'Release is not stable')
    assets = {a['name']: a for a in release['assets']}
    require(len(assets) == len(release['assets']), 'Duplicate release asset names')
    require(set(assets) == set(expected) | set(extra), 'Release asset roster changed')
    for name, digest in expected.items():
        require(assets[name]['digest'] == 'sha256:' + digest, 'Release digest changed: ' + name)
        if ids:
            require(assets[name]['id'] == ids[name], 'Release asset replaced: ' + name)
    return assets

def release_now():
    release = api(f'repos/{REPO}/releases/tags/{TAG}')
    require(api(f'repos/{REPO}/releases/latest')['id'] == release['id'],
            'A newer core release exists; rebase the refresh')
    return release

def green(repo, run, head):
    result = api(f'repos/{repo}/actions/runs/{run}')
    require(result['head_sha'] == head and result['status'] == 'completed'
            and result['conclusion'] == 'success', 'Required CI not green: ' + str(run))

def prepare():
    from refresh_release_addon import refresh
    from verify_published_addon_bundle import validate_bundle
    work = Path('work/r136')
    require(not work.exists(), 'Refusing to reuse a staging directory')
    (work / 'original').mkdir(parents=True)
    (work / 'jars').mkdir()
    baseline = release_now()
    lease(baseline, HASHES)
    (work / 'release-before.json').write_text(json.dumps(baseline, indent=2) + '\n')
    # Production sources must still match the already-tested bundle; only these release files may differ.
    allowed = {'scripts/publish_r136.py', 'scripts/test_publish_r136.py',
               '.github/workflows/refresh-v4.1.74-r136.yml', 'docs/addon-bundle-r136.md'}
    changed = set(command('git', 'diff', '--name-only', TESTED, 'HEAD').splitlines())
    require(changed <= allowed, 'Untested source change in publication: ' + repr(changed - allowed))
    require(not command('git', 'diff', '--name-only', CORE, TESTED, '--',
                        'src/main', 'build.gradle.kts', 'gradle.properties', 'gradle').strip(),
            'Candidate production core differs from the released core')
    green(REPO, 38598879430, TESTED)
    green(REPO, 38598879446, TESTED)
    jobs = api(f'repos/{REPO}/actions/runs/38598879430/jobs?per_page=100')['jobs']
    require(len([j for j in jobs if j['name'].startswith('Verify wickidcow/')]) == 45
            and all(j['conclusion'] == 'success' for j in jobs), '45-addon CI was incomplete')
    native = api(f'repos/{REPO}/actions/jobs/115981137598')
    require(native['head_sha'] == TESTED and any(s['name'].startswith('Probe native Networks')
            and s['conclusion'] == 'success' for s in native['steps']), 'Native test was skipped')
    command('gh', 'release', 'download', TAG, '--repo', REPO, '--dir', str(work / 'original'),
            *[arg for name in HASHES for arg in ('--pattern', name)])
    for name, digest in HASHES.items():
        require(sha(work / 'original' / name) == digest, 'Downloaded baseline digest mismatch')
    matrix = json.loads(Path('compatibility/sfl-addon-release-matrix.json').read_text())
    require(matrix['bundle_revision'] == 136 and len(matrix['addons']) == 45, 'Incorrect matrix')
    pins = {a['repository']: a['source_commit'] for a in matrix['addons']}
    release_records = []
    for update in UPDATES:
        repo = update['repository']
        green(repo, update['run'], update['source'])
        require(pins[repo] == update['source'], 'Tested source selection changed')
        tag = 'v' + update['version']
        release = api(f'repos/{repo}/releases/tags/{tag}')
        require(not release['draft'] and not release['prerelease'], 'Addon release is not stable')
        require(release['target_commitish'] == update['release_source'], 'Addon release target changed')
        ref = api(f'repos/{repo}/git/ref/tags/{tag}')['object']
        for _ in range(5):
            if ref['type'] != 'tag':
                break
            ref = api(f'repos/{repo}/git/tags/{ref["sha"]}')['object']
        require(ref['type'] == 'commit' and ref['sha'] == update['release_source'], 'Addon tag moved')
        released_tree = api(f'repos/{repo}/git/commits/{update["release_source"]}')['tree']['sha']
        tested_tree = api(f'repos/{repo}/git/commits/{update["source"]}')['tree']['sha']
        require(released_tree == tested_tree, 'Released code differs from tested code')
        runs = api(f'repos/{repo}/actions/runs?head_sha={update["release_source"]}&per_page=100')['workflow_runs']
        require(any(r['event'] == 'push' and r['path'] == '.github/workflows/build.yml'
                    and r['status'] == 'completed' and r['conclusion'] == 'success' for r in runs),
                'Exact merged addon release build is not green')
        assets = [a for a in release['assets'] if a['name'] == update['new_jar']]
        require(len(assets) == 1 and re.fullmatch(r'sha256:[0-9a-f]{64}', assets[0].get('digest', '')),
                'Missing checksummed official JAR')
        command('gh', 'release', 'download', tag, '--repo', repo, '--pattern', update['new_jar'],
                '--dir', str(work / 'jars'))
        digest = sha(work / 'jars' / update['new_jar'])
        require('sha256:' + digest == assets[0]['digest'], 'Official JAR download digest mismatch')
        release_records.append({**update, 'sha256': digest, 'release_url': release['html_url'],
                                'tree': tested_tree, 'asset_id': assets[0]['id']})
    original = work / 'original' / ZIP
    with zipfile.ZipFile(original) as archive:
        old_manifest = json.loads(archive.read('SF_ADDON_MANIFEST.json'))
    require(old_manifest['bundle_revision'] == 135, 'Input is not r135')
    other = {r['repository']: r['commit'] for r in old_manifest['addons']
             if r['repository'] not in {u['repository'] for u in UPDATES}}
    require(len(other) == 43 and all(pins[r] == c for r, c in other.items()), 'Other source pins changed')
    outputs = []
    for repetition in range(2):
        source = original
        for index, update in enumerate(release_records):
            stage_matrix = copy.deepcopy(matrix)
            for future in release_records[index + 1:]:
                for row in stage_matrix['addons']:
                    if row['repository'] == future['repository']:
                        row['source_commit'] = future['old_commit']
            config = dict(repository=update['repository'], old_jar=update['old_jar'],
                          new_jar=update['new_jar'], old_commit=update['old_commit'],
                          new_commit=update['source'], new_version=update['version'],
                          new_sha256=update['sha256'], old_bundle_sha256=sha(source),
                          core_source_commit=CORE, release_tag=TAG, expected_addons=45, bundle_revision=136,
                          new_distributable_api='1.21.11-R0.1-SNAPSHOT',
                          new_build_core_version=update['core'], new_paper_26_3_api=update['paper'],
                          compatibility_note=f'r136 {update["new_jar"]}; official release source '
                          f'{update["release_source"]} has identical tree to tested lock {update["source"]}. '
                          'No core, resource pack, player data or unrelated addon changes.')
            destination = work / f'build-{repetition}-stage-{index}.zip'
            refresh(config, stage_matrix, source, work / 'jars' / update['new_jar'], destination)
            source = destination
        outputs.append(source)
    require(sha(outputs[0]) == sha(outputs[1]), 'Archive rebuild is not deterministic')
    output = work / ZIP
    output.write_bytes(outputs[0].read_bytes())
    result = validate_bundle(output)
    require(result['addon_count'] == 45 and result['core_source_commit'] == CORE, 'Final bundle invalid')
    with zipfile.ZipFile(original) as before, zipfile.ZipFile(output) as after:
        unchanged = {n for n in before.namelist() if n.endswith('.jar')} - {u['old_jar'] for u in UPDATES}
        require(len(unchanged) == 43 and all(before.read(n) == after.read(n) for n in unchanged),
                'Unrelated JAR bytes changed')
        final = json.loads(after.read('SF_ADDON_MANIFEST.json'))
        require({r['repository']: r['commit'] for r in final['addons']} == pins, 'Final source pins differ')
    report = dict(bundle_revision=136, bundle_sha256=sha(output), addon_count=45, unchanged_addons=43,
                  core_source_commit=CORE, baseline_hashes=HASHES, releases=release_records,
                  tested_bundle_commit=TESTED, bundle_run=38598879430, full_stack_run=38598879446)
    (work / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

def publish():
    work = Path('work/r136')
    report = json.loads((work / 'validation.json').read_text())
    before = json.loads((work / 'release-before.json').read_text())
    original_assets = lease(before, HASHES)
    ids = {name: a['id'] for name, a in original_assets.items()}
    candidate = work / ZIP
    require(sha(candidate) == report['bundle_sha256'] and report['unchanged_addons'] == 43,
            'Staged artifact changed')
    live = release_now()
    require(live['id'] == before['id'], 'Release was recreated')
    lease(live, HASHES, ids)
    temporary_name = ZIP + '.r136-pending'
    rollback_name = ZIP + '.r135-rollback'
    temporary = work / temporary_name
    temporary.write_bytes(candidate.read_bytes())
    command('gh', 'release', 'upload', TAG, str(temporary), '--repo', REPO)
    live = release_now()
    assets = lease(live, HASHES, ids, (temporary_name,))
    new_id = assets[temporary_name]['id']
    require(assets[temporary_name]['digest'] == 'sha256:' + report['bundle_sha256'], 'Uploaded digest differs')
    old_id = ids[ZIP]
    api(f'repos/{REPO}/releases/assets/{old_id}', '-X', 'PATCH', '-f', 'name=' + rollback_name)
    try:
        api(f'repos/{REPO}/releases/assets/{new_id}', '-X', 'PATCH', '-f', 'name=' + ZIP)
        expected = {**HASHES, ZIP: report['bundle_sha256']}
        new_ids = {**ids, ZIP: new_id}
        lease(release_now(), expected, new_ids, (rollback_name,))
        # Verify actual public bytes before removing the still-available rollback archive.
        verify = work / 'public'
        verify.mkdir()
        command('gh', 'release', 'download', TAG, '--repo', REPO, '--pattern', ZIP, '--dir', str(verify))
        require(sha(verify / ZIP) == report['bundle_sha256'], 'Public ZIP download differs')
    except Exception:
        # Remove only OUR new asset, never an unrelated concurrent upload; restore the original ID.
        api(f'repos/{REPO}/releases/assets/{new_id}', '-X', 'DELETE')
        api(f'repos/{REPO}/releases/assets/{old_id}', '-X', 'PATCH', '-f', 'name=' + ZIP)
        raise
    api(f'repos/{REPO}/releases/assets/{old_id}', '-X', 'DELETE')
    final = release_now()
    lease(final, expected, new_ids)
    note = Path('docs/addon-bundle-r136.md').read_text()
    body = final.get('body') or ''
    if '## Addon bundle refresh — revision 136' not in body:
        body = body.rstrip() + '\n\n' + note.rstrip() + '\n\nZIP SHA-256: `' + report['bundle_sha256'] + '`\n'
        notes = work / 'notes.md'
        notes.write_text(body)
        command('gh', 'release', 'edit', TAG, '--repo', REPO, '--notes-file', str(notes))
    (work / 'release-after.json').write_text(json.dumps(release_now(), indent=2) + '\n')
    print('PUBLISHED r136:', report['bundle_sha256'], '; 43 unchanged JARs; core and RP unchanged')

if __name__ == '__main__':
    require(len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'publish'), 'Use prepare or publish')
    globals()[sys.argv[1]]()
