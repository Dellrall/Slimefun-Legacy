#!/usr/bin/env python3
"""Prepare narrowly scoped Git objects; never move a branch, merge, publish, or deploy."""
from pathlib import Path
import base64
import hashlib
import json
import os
import subprocess
import sys
from prepare_networks_r139 import admit, CONFIG, PATCHES

BASE = '88e0b1e416c473485b2912dfe8413780d625a169'
BASE_TREE = 'ee53e3490ee25ff04394bde8ee0555ceccb7e5b2'
REPO = 'wickidcow/Slimefun-Legacy'


def api(endpoint, payload=None):
    args = ['gh', 'api', f'repos/{REPO}/' + endpoint]
    if payload is not None:
        args += ['--method', 'POST', '--input', '-']
    result = subprocess.run(args, input=None if payload is None else json.dumps(payload).encode(),
                            check=True, capture_output=True, timeout=90)
    return json.loads(result.stdout)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    require(api('git/ref/heads/master')['object']['sha'] == BASE, 'Master moved; rebase instead of overwriting')
    artifact = Path('candidate')
    candidate_hash = hashlib.sha256((artifact / 'SF_Addons_1.21.11-26.3.zip').read_bytes()).hexdigest()
    require(candidate_hash == '541708ca969bb6d6c7a0b11510e856b221c2dbd984e6523404a53ebdaa60ff1c', 'Wrong candidate')
    admit()
    # The three integration files must match the exact runtime-tested candidate tooling.
    for name in PATCHES:
        require(Path(name).read_bytes() == (artifact / 'source' / name).read_bytes(), 'Tested tooling drift: ' + name)
    added = []
    test = Path('tests/runtime_contracts/test_networks_r139_admission.py')
    test.parent.mkdir(parents=True, exist_ok=True)
    test.write_bytes(Path('maintenance/test_networks_r139_admission.py').read_bytes())
    added.append(test.as_posix())
    env = dict(os.environ, SFL_R139_SOURCE_ROOT=str(Path.cwd()),
               SFL_R139_NETWORKS_JAR=str((artifact / 'SF_Networks1.0.56.jar').resolve()))
    result = subprocess.run([sys.executable, str(test)], env=env, capture_output=True, text=True)
    Path('integration-admission-tests.log').write_text(result.stdout + result.stderr)
    require(result.returncode == 0, 'New r139 offline admission tests failed')
    config = Path('compatibility/networks-r139-release.json')
    config.write_text(json.dumps(CONFIG, indent=2) + '\n')
    added.append(config.as_posix())
    note = Path('docs/releases/addons-r139-networks.md')
    note.write_text('''# Networks-only addon bundle r139 — integration candidate, not published

This selection replaces only Networks 1.0.55 with the published 1.0.56 release at
`c0b388e45e929c1a721d7a8aa968b2e0d4fc10e9`. It retains all 44 other r137 addon
source pins. r138 remains reserved for separate MagicExpansion work; this is not
permission to replace a newer published selection with the old r137 baseline.

The separately prepared exact-byte ZIP is
`541708ca969bb6d6c7a0b11510e856b221c2dbd984e6523404a53ebdaa60ff1c`.
Its Networks JAR is
`25a1bbeef780bb3d263506892df3b8b8cb42ec3be5ee5d36393c8fe1e7c52d89`.
All 44 other JARs are byte-identical to published r137. The published Slimefun
4.1.74 core and resource pack are unchanged. A source-rebuilt CI bundle is not
silently substituted for this exact tested ZIP.

Exact-byte native validation is tracked at
https://github.com/wickidcow/Slimefun-Legacy/actions/runs/38823000873 . Check its
actual completed outcome and retained evidence before publication; this note
alone does not assert a successful workflow. The fixture boots the entire
selection twice on Paper 1.21.11/26.2/26.3 and experimental Purpur 26.3, checks
real Networks/Fluffy conservation on Paper 26.3, and checks Black Market receipts
across four JVM phases on each platform. It is not a live-world or crash proof.

The inherited r137 exact-byte workflow is historical and now manual-only: its
lease refers to the pre-r137 published asset roster and cannot validate a newer
bundle. Its assertions are retained. New r139 admission tests run independently
alongside the existing source-bundle and full-stack workflows; no guard is
removed from the runtime code. The new tests use the exact Networks release,
synthetic unrelated plugin bytes and a mocked compiler; they never start Java.

No item IDs, recipes, production rates, plugin production source, serialization
formats, core release identity or live server data are changed in this PR.
The original Infinity Dust Extractor source mutation remains unexplained;
Networks 1.0.56 fixes destructive VOID cleanup, not every possible source conflict.

Before publication, finish exact-head integration checks, verify the frozen
candidate/native evidence, recheck master and current release asset leases,
reconcile concurrent core/MagicExpansion work, and obtain the required approval.
Keep the previous published ZIP as a rollback copy. Never overwrite the published
core/resource-pack files or install all optional addons indiscriminately.
''')
    added.append(note.as_posix())
    historical = Path('.github/workflows/r137-release-candidate.yml')
    text = historical.read_text()
    require(text.startswith('name: r137 exact-byte release candidate\n\non:\n') and text.count('\npermissions:\n') == 1,
            'Historical workflow changed; review it')
    historical.write_text('name: Historical r137 exact-byte release candidate\n\non:\n  workflow_dispatch:\n\n'
                          '# Historical pre-r137 release lease; newer selections have separate validation.\n'
                          'permissions:\n' + text.split('\npermissions:\n', 1)[1])
    added.append(historical.as_posix())
    workflow = Path('.github/workflows/networks-r139-contracts.yml')
    workflow.write_text('''name: Networks r139 admission contracts
on:
  pull_request:
    paths:
      - 'compatibility/sfl-addon-release-matrix.json'
      - 'compatibility/networks-r139-release.json'
      - 'scripts/runtime/r135_fluffy_networks/**'
      - 'scripts/runtime/black_market/**'
      - 'tests/runtime_contracts/test_networks_r139_admission.py'
      - '.github/workflows/networks-r139-contracts.yml'
  workflow_dispatch:
permissions:
  contents: read
jobs:
  contracts:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v6
      - name: Download exact public Networks fixture
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          mkdir -p .ci/networks-r139
          gh release download v1.0.56 --repo wickidcow/SF_NetworksExp --pattern SF_Networks1.0.56.jar --dir .ci/networks-r139
          echo '25a1bbeef780bb3d263506892df3b8b8cb42ec3be5ee5d36393c8fe1e7c52d89  .ci/networks-r139/SF_Networks1.0.56.jar' | sha256sum --check
      - name: Preserve existing admission contracts
        run: |
          python3 -m unittest discover -s scripts -p test_native_storage_probe_contracts.py -v
          python3 -m unittest discover -s scripts -p test_black_market_probe_contracts.py -v
      - name: Check r139 acceptance and rejection without starting a server
        run: |
          SFL_R139_SOURCE_ROOT="$PWD" SFL_R139_NETWORKS_JAR="$PWD/.ci/networks-r139/SF_Networks1.0.56.jar" \
            python3 tests/runtime_contracts/test_networks_r139_admission.py
''')
    added.append(workflow.as_posix())
    names = list(PATCHES) + added
    require(len(names) == len(set(names)) == 8, 'Unexpected integration scope')
    subprocess.run(['git', 'diff', '--check', '--', *names], check=True)
    # Check that the source selection changed only revision and the Networks lock.
    original = json.loads(subprocess.check_output(['git', 'show', BASE + ':compatibility/sfl-addon-release-matrix.json']))
    current = json.loads(Path('compatibility/sfl-addon-release-matrix.json').read_text())
    original['bundle_revision'] = 139
    next(r for r in original['addons'] if r['repository'] == CONFIG['repository'])['source_commit'] = CONFIG['new_commit']
    require(original == current, 'Unrelated source pin changed')
    require(api('git/ref/heads/master')['object']['sha'] == BASE, 'Master moved during preparation')
    tree = []
    for name in names:
        data = Path(name).read_bytes()
        blob = api('git/blobs', {'content': base64.b64encode(data).decode(), 'encoding': 'base64'})
        expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        require(blob['sha'] == expected, 'Remote blob mismatch')
        tree.append({'path': name, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
    created_tree = api('git/trees', {'base_tree': BASE_TREE, 'tree': tree})
    commit = api('git/commits', {'message': 'chore(bundle): pin Networks 1.0.56 for r139 without changing other addons\n\nCarry forward the exact published Networks safety fix and r139 native admission metadata. Retain the other 44 source locks, core identity, resource pack and production code. Archive the historical r137 automatic release-lease gate, retain its assertions, and add real-byte offline admission tests. Integration CI, exact-byte evidence and separate publication approval remain required.',
                               'tree': created_tree['sha'], 'parents': [BASE]})
    Path('prepared-commit.json').write_text(json.dumps({'commit': commit['sha'], 'tree': created_tree['sha'],
        'base': BASE, 'files': tree, 'candidate_sha256': candidate_hash,
        'scope': '8 metadata, test and workflow files; no branch/ref or release mutation',
        'tests': 'Existing 34 and new 12 offline admission tests passed; no local Gradle or JVM claim'}, indent=2) + '\n')
    print(Path('prepared-commit.json').read_text())

if __name__ == '__main__':
    main()
