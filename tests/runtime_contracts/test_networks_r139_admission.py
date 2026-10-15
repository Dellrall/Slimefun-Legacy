"""Offline admission contracts: real published Networks bytes, synthetic other plugins, no JVM."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(os.environ.get('SFL_R139_SOURCE_ROOT', Path(__file__).resolve().parents[2])).resolve()
NETWORK = 'wickidcow/SF_NetworksExp'
COMMIT = 'c0b388e45e929c1a721d7a8aa968b2e0d4fc10e9'
JAR = 'SF_Networks1.0.56.jar'
HASH = '25a1bbeef780bb3d263506892df3b8b8cb42ec3be5ee5d36393c8fe1e7c52d89'
NETWORK_BYTES = Path(os.environ['SFL_R139_NETWORKS_JAR']).read_bytes()
if hashlib.sha256(NETWORK_BYTES).hexdigest() != HASH:
    raise RuntimeError('The offline fixture requires the exact published Networks JAR')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

native = load('r139_native_contract', ROOT / 'scripts/runtime/r135_fluffy_networks/run_probe.py')
black = load('r139_black_contract', ROOT / 'scripts/runtime/black_market/run_probe.py')


class R139Admission(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        previous = Path.cwd()
        os.chdir(self.home)
        self.addCleanup(os.chdir, previous)
        self.work = self.home / 'build/full-stack-26.3'
        self.plugins = self.work / 'plugins'
        self.plugins.mkdir(parents=True)
        for name, text in {
            'smoke-result.txt': 'runtime smoke: PASS\n',
            'server.jar': 'OFFLINE SYNTHETIC FIXTURE, NOT A SERVER',
            'eula.txt': 'eula=true\n',
            'server.properties': 'online-mode=false\nlevel-name=full-stack-smoke-world\nenable-rcon=false\nenable-query=false\n',
            'runtime-build.txt': 'Offline admission fixture only',
            'plugins/Slimefun-Legacy-full-stack.jar': 'synthetic core',
        }.items():
            (self.work / name).write_text(text)
        rows = [
            {'repository': NETWORK, 'commit': COMMIT, 'jar': JAR},
            {'repository': black.MAGIC, 'commit': black.MAGIC_COMMIT, 'jar': black.MAGIC_JAR},
            {'repository': 'wickidcow/SF_FluffyMachines', 'commit': '3d5286877e2307b4b9bc48be886d14d75e6889c6',
             'jar': 'SF_FluffyMachines26.2.16.jar'},
        ]
        rows.extend({'repository': f'fixture/Addon{i}', 'commit': 'a' * 40, 'jar': f'Addon{i}.jar'} for i in range(42))
        self.blobs = {}
        for row in rows:
            data = NETWORK_BYTES if row['repository'] == NETWORK else ('synthetic ' + row['repository']).encode()
            self.blobs[row['jar']] = data
            row['sha256'] = hashlib.sha256(data).hexdigest()
            (self.plugins / row['jar']).write_bytes(data)
        self.manifest = {'bundle_revision': 139, 'addons': rows}
        self.row = rows[0]
        self.bundle = self.home / 'fixture.zip'
        self.rewrite()
        self.java = self.home / 'jdk/bin/java'
        self.java.parent.mkdir(parents=True)
        self.java.write_text('NOT EXECUTABLE')
        self.java.with_name('javac').write_text('NOT EXECUTABLE')
        self.sources = self.home / 'probe'
        self.sources.mkdir()
        (self.sources / 'plugin.yml').write_text('name: OfflineContractOnly\n')

    def rewrite(self):
        with zipfile.ZipFile(self.bundle, 'w') as archive:
            archive.writestr('SF_ADDON_MANIFEST.json', json.dumps(self.manifest))
            for name, data in self.blobs.items():
                archive.writestr(name, data)

    def native_prepare(self):
        with patch.object(native, 'HERE', self.sources), \
             patch.object(native.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as compiler, \
             patch.object(native.subprocess, 'Popen', side_effect=AssertionError('No JVM may launch')):
            return native.prepare(self.work, self.bundle, self.java), compiler

    def test_native139_admits_exact_source_without_claiming_runtime_pass(self):
        report, compiler = self.native_prepare()
        self.assertEqual(report['bundle_revision'], 139)
        self.assertEqual(report['status'], 'STARTED')
        self.assertNotIn('result', report)
        self.assertEqual(report['tested_addons'][NETWORK]['sha256'], HASH)
        compiler.assert_called_once()

    def test_native139_rejects_old_networks_source(self):
        self.row['commit'] = 'bcdef34d362dc74aa1aab23c8961a629daa79950'
        self.rewrite()
        with self.assertRaisesRegex(RuntimeError, 'source mismatch'):
            self.native_prepare()

    def test_native139_rejects_wrong_filename(self):
        self.row['jar'] = 'SF_Networks1.0.55.jar'
        self.rewrite()
        with self.assertRaisesRegex(RuntimeError, 'source mismatch'):
            self.native_prepare()

    def test_native139_rejects_altered_staged_bytes(self):
        (self.plugins / JAR).write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'digest mismatch'):
            self.native_prepare()

    def test_native139_rejects_failed_double_boot(self):
        (self.work / 'smoke-result.txt').write_text('FAIL')
        with self.assertRaisesRegex(RuntimeError, 'baseline did not pass'):
            self.native_prepare()

    def test_black139_admits_exact_release_without_writes(self):
        before = {p.relative_to(self.work): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.work.rglob('*') if p.is_file()}
        report = black.validate_fixture(self.work, self.bundle)
        self.assertEqual(report['bundle_revision'], 139)
        self.assertEqual(report['result'], 'STARTED')
        self.assertEqual(report['tested_addons'][NETWORK]['sha256'], HASH)
        self.assertEqual(before, {p.relative_to(self.work): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in self.work.rglob('*') if p.is_file()})

    def test_black139_rejects_wrong_networks_hash(self):
        self.row['sha256'] = 'a' * 64
        self.rewrite()
        with self.assertRaisesRegex(RuntimeError, 'Wrong exact Networks'):
            black.validate_fixture(self.work, self.bundle)

    def test_black139_rejects_wrong_networks_source(self):
        self.row['commit'] = '0' * 40
        self.rewrite()
        with self.assertRaisesRegex(RuntimeError, 'Wrong exact Networks'):
            black.validate_fixture(self.work, self.bundle)

    def test_black139_rejects_missing_networks_repository(self):
        self.row['repository'] = 'fixture/other'
        self.rewrite()
        with self.assertRaisesRegex(RuntimeError, 'Wrong exact Networks'):
            black.validate_fixture(self.work, self.bundle)

    def test_black139_rejects_unreviewed_magic_source(self):
        self.manifest['addons'][1]['commit'] = '0' * 40
        self.rewrite()
        with self.assertRaisesRegex(RuntimeError, 'Wrong MagicExpansion'):
            black.validate_fixture(self.work, self.bundle)

    def test_reserved138_is_not_implicitly_admitted(self):
        self.manifest['bundle_revision'] = 138
        self.rewrite()
        with self.assertRaisesRegex(RuntimeError, 'requires candidate'):
            black.validate_fixture(self.work, self.bundle)
        with self.assertRaises(RuntimeError):
            self.native_prepare()

    def test_noninteger139_is_rejected(self):
        self.manifest['bundle_revision'] = 139.0
        self.rewrite()
        with self.assertRaises(RuntimeError):
            black.validate_fixture(self.work, self.bundle)
        with self.assertRaises(RuntimeError):
            self.native_prepare()


if __name__ == '__main__':
    unittest.main(verbosity=2)
