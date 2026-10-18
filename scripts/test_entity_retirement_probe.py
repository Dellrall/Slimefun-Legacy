"""Fail-closed artifact and native-receipt controls for the permanent probe."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

SOURCE = "1" * 40
PATH = Path(__file__).parent / "runtime/entity_retirement/run_probe.py"
SPEC = importlib.util.spec_from_file_location("entity_retirement_probe", PATH)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def receipt():
    cases = {}
    for name in PROBE.CASES:
        cancelled = name == "explicitly_cancelled"
        retired = name.startswith("rejected_") or name == "retired_after_acceptance"
        cases[name] = {"work": int(not retired and not cancelled), "retired": int(retired),
                       "owned": int(name.startswith("live_")), "cancelled": retired or cancelled}
    return {"schema": 1, "status": "PASS", "token": "test-token", "core_source": SOURCE,
            "core_version": "4.1.76", "software": "Folia", "minecraft": "26.3",
            "server_version": "26.3-3-test (MC: 26.3)", "folia": True,
            "native_removed_entity_rejected": True, "assertions": 27, "active_handles": 0,
            "cases": cases, "failures": []}


class NativeReceiptContracts(unittest.TestCase):
    def validate(self, data, **options):
        PROBE.validate_result(data, source=SOURCE, version="4.1.76", software="Folia", minecraft="26.3",
                              build="3", token="test-token", **options)

    def test_complete_receipt_passes(self):
        self.validate(receipt())

    def test_source_platform_and_build_must_match(self):
        for key, value in (("core_source", "2" * 40), ("software", "Purpur"), ("minecraft", "26.2"),
                           ("server_version", "26.3-4-other"), ("folia", False)):
            with self.subTest(key=key):
                data = copy.deepcopy(receipt())
                data[key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(data)

    def test_missing_phase_or_incomplete_assertions_fail(self):
        missing = receipt()
        del missing["cases"]["rejected_delayed"]
        truncated = receipt()
        truncated["assertions"] = 26
        for data in (missing, truncated):
            with self.assertRaises(RuntimeError):
                self.validate(data)

    def test_duplicate_cleanup_does_not_count_as_success(self):
        data = receipt()
        data["cases"]["rejected_immediate"]["retired"] = 2
        with self.assertRaises(RuntimeError):
            self.validate(data)

    def test_live_work_must_run_on_owner(self):
        data = receipt()
        data["cases"]["live_immediate"]["owned"] = 0
        with self.assertRaises(RuntimeError):
            self.validate(data)

    def test_baseline_control_cannot_be_reported_as_passing_candidate(self):
        data = receipt()
        data["status"] = "FAIL"
        data["failures"] = list(PROBE.REJECTION_FAILURES)
        for name, case in data["cases"].items():
            if name.startswith("rejected_"):
                case["retired"] = 0
        with self.assertRaises(RuntimeError):
            self.validate(data)
        self.validate(data, expected_failure=True)
        data["failures"].append("unexpected failure")
        with self.assertRaises(RuntimeError):
            self.validate(data, expected_failure=True)

    def test_shutdown_requires_real_completion(self):
        PROBE.validate_completion({"token": "test-token", "server_stopping": True}, "test-token", 0)
        for data, exit_code in (({}, 0), ({"token": "other", "server_stopping": True}, 0),
                                ({"token": "test-token", "server_stopping": False}, 0),
                                ({"token": "test-token", "server_stopping": True}, 1)):
            with self.assertRaises(RuntimeError):
                PROBE.validate_completion(data, "test-token", exit_code)

    def test_shutdown_timeout_fails_even_if_termination_returns_zero(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [PROBE.subprocess.TimeoutExpired("native-server", 60), 0]
        with self.assertRaisesRegex(RuntimeError, "Native shutdown timed out"):
            PROBE.stop(process)
        process.terminate.assert_called_once_with()
        process.stdin.close.assert_called_once_with()

    def test_result_file_and_completion_marker_are_both_required_before_shutdown(self):
        for has_result, has_marker in ((True, False), (False, True), (True, True)):
            with self.subTest(result=has_result, marker=has_marker):
                process = Mock()
                process.poll.return_value = None
                evidence = Mock()
                evidence.is_file.return_value = has_result
                native_log = Mock()
                native_log.is_file.return_value = True
                native_log.read_text.return_value = "RETIREMENT_PROBE PASS" if has_marker else ""
                console = Mock()
                console.read_text.return_value = ""
                times = [0, 0, 0] if has_result and has_marker else [0, 0, 2]
                with patch.object(PROBE.time, "monotonic", side_effect=times), \
                        patch.object(PROBE.time, "sleep"):
                    if has_result and has_marker:
                        PROBE.wait_for_result(process, native_log, console, evidence, timeout=1)
                    else:
                        with self.assertRaisesRegex(RuntimeError, "Native lifecycle probe did not complete"):
                            PROBE.wait_for_result(process, native_log, console, evidence, timeout=1)

    def test_stdout_marker_cannot_replace_a_missing_or_incomplete_native_log(self):
        for native_exists in (False, True):
            with self.subTest(native_exists=native_exists):
                process = Mock()
                process.poll.return_value = None
                evidence = Mock()
                evidence.is_file.return_value = True
                native_log = Mock()
                native_log.is_file.return_value = native_exists
                native_log.read_text.return_value = ""
                console = Mock()
                console.read_text.return_value = "Done (1s)! RETIREMENT_PROBE PASS"
                for wait, extra in ((PROBE.wait_for_startup, ()), (PROBE.wait_for_result, (evidence,))):
                    with patch.object(PROBE.time, "monotonic", side_effect=[0, 0, 2]), \
                            patch.object(PROBE.time, "sleep"), self.assertRaisesRegex(RuntimeError, "did not complete"):
                        wait(process, native_log, console, *extra, timeout=1)

    def test_either_log_stream_rejects_native_failures(self):
        for failure_stream in ("native", "stdout"):
            for marker in PROBE.BAD_LOG_MARKERS:
                with self.subTest(stream=failure_stream, marker=marker):
                    native_log = Mock()
                    native_log.is_file.return_value = True
                    native_log.read_text.return_value = marker if failure_stream == "native" else "RETIREMENT_PROBE PASS"
                    console = Mock()
                    console.read_text.return_value = marker if failure_stream == "stdout" else ""
                    with self.assertRaisesRegex(RuntimeError, "Native lifecycle probe failed"):
                        PROBE.read_native_output(native_log, console)

    def test_startup_and_completion_reject_late_evidence_and_process_exit(self):
        for wait, extra in ((PROBE.wait_for_startup, ()), (PROBE.wait_for_result, (Mock(is_file=lambda: True),))):
            for clock, polls in (([0, 2], [None]), ([0, 0, 2], [None, None]), ([0, 0], [None, 0])):
                with self.subTest(wait=wait.__name__, clock=clock, polls=polls):
                    process = Mock()
                    process.poll.side_effect = polls
                    native_log = Mock()
                    native_log.is_file.return_value = True
                    native_log.read_text.return_value = "Done (1s)! RETIREMENT_PROBE PASS"
                    console = Mock()
                    console.read_text.return_value = ""
                    with patch.object(PROBE.time, "monotonic", side_effect=clock), \
                            patch.object(PROBE.time, "sleep"), self.assertRaises(RuntimeError):
                        wait(process, native_log, console, *extra, timeout=1)

    def test_startup_accepts_fresh_native_log_when_stdout_stops_receiving_events(self):
        process = Mock()
        process.poll.return_value = None
        native_log = Mock()
        native_log.is_file.return_value = True
        native_log.read_text.return_value = "Done (1s)!"
        console = Mock()
        console.read_text.return_value = "Launcher bootstrap only"
        with patch.object(PROBE.time, "monotonic", side_effect=[0, 0, 0]):
            PROBE.wait_for_startup(process, native_log, console, timeout=1)


class ArtifactContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.core = self.root / "candidate.jar"
        with zipfile.ZipFile(self.core, "w") as jar:
            jar.writestr("git.properties", f"git.source.commit={SOURCE}\ngit.commit.id={SOURCE}\ngit.build.version=4.1.76\n")
            jar.writestr("plugin.yml", "name: Slimefun\nversion: 4.1.76\n")
        self.metadata = {"schema": 1, "source_commit": SOURCE, "core_version": "4.1.76",
                         "core_sha256": hashlib.sha256(self.core.read_bytes()).hexdigest()}

    def test_exact_core_is_accepted(self):
        self.assertEqual("4.1.76", PROBE.validate_core(self.core, self.metadata, SOURCE))

    def test_unknown_or_wrong_source_is_rejected(self):
        for source in ("unknown", "2" * 40):
            with self.assertRaises(RuntimeError):
                PROBE.validate_core(self.core, self.metadata, source)

    def test_wrong_artifact_hash_is_rejected(self):
        metadata = copy.deepcopy(self.metadata)
        metadata["core_sha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            PROBE.validate_core(self.core, metadata, SOURCE)

    def test_embedded_source_must_match_metadata(self):
        metadata = copy.deepcopy(self.metadata)
        metadata["source_commit"] = "2" * 40
        with self.assertRaises(RuntimeError):
            PROBE.validate_core(self.core, metadata, "2" * 40)

    def test_existing_fixture_is_never_modified(self):
        metadata = self.root / "metadata.json"
        metadata.write_text(json.dumps(self.metadata))
        existing = self.root / "existing-server"
        existing.mkdir()
        sentinel = existing / "player-data"
        sentinel.write_bytes(b"preserve existing data")
        args = SimpleNamespace(core=self.core, core_metadata=metadata, expected_source=SOURCE,
                               server_jar=self.core, server_sha256=PROBE.digest(self.core), software="Folia",
                               expect_missing_retirement=False, work_dir=existing)
        with self.assertRaisesRegex(RuntimeError, "Refusing an existing fixture"):
            PROBE.run(args)
        self.assertEqual(b"preserve existing data", sentinel.read_bytes())
        self.assertEqual(["player-data"], [path.name for path in existing.iterdir()])


if __name__ == "__main__":
    unittest.main()
