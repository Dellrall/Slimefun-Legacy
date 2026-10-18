#!/usr/bin/env python3
"""Run the entity-retirement regression in a new, disposable native server."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
PLUGIN = "RetirementProbe"
CASES = {"rejected_immediate", "rejected_delayed", "rejected_zero_delay", "live_immediate",
         "live_delayed", "retired_after_acceptance", "explicitly_cancelled"}
REJECTION_FAILURES = ["rejected_delayed:retired", "rejected_immediate:retired", "rejected_zero_delay:retired"]
BAD_LOG_MARKERS = ("RETIREMENT_PROBE unexpected failure", "NoClassDefFoundError", "NoSuchMethodError",
                   "Error occurred while enabling", "Error occurred while disabling")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def properties(data: bytes) -> dict[str, str]:
    return dict(line.split("=", 1) for line in data.decode("utf-8").splitlines()
                if "=" in line and not line.startswith(("#", "!")))


def validate_core(core: Path, metadata: dict, expected_source: str) -> str:
    require(re.fullmatch(r"[0-9a-f]{40}", expected_source) is not None,
            "Expected source must be a full Git commit")
    require(core.is_file() and not core.is_symlink(), "Core must be a regular file")
    require(metadata.get("schema") == 1 and metadata.get("source_commit") == expected_source,
            "Candidate metadata source mismatch")
    require(metadata.get("core_sha256") == digest(core), "Candidate artifact checksum mismatch")
    with zipfile.ZipFile(core) as jar:
        require(jar.testzip() is None and len(jar.namelist()) == len(set(jar.namelist())),
                "Invalid core archive")
        git = properties(jar.read("git.properties"))
        require(git.get("git.source.commit") == expected_source
                and git.get("git.commit.id") == expected_source, "Embedded core source mismatch")
        version = git.get("git.build.version", "")
        require(re.fullmatch(r"[A-Za-z0-9.+_-]+", version) is not None, "Invalid core version")
        require(metadata.get("core_version") == version, "Candidate metadata version mismatch")
        descriptor = re.search(r"^version:\s*['\"]?([^'\"\s]+)['\"]?\s*$",
                               jar.read("plugin.yml").decode("utf-8"), re.MULTILINE)
        require(descriptor is not None and descriptor.group(1) == version, "Core descriptor version mismatch")
    return version


def validate_result(data: dict, *, source: str, version: str, software: str, minecraft: str,
                    build: str, token: str, expected_failure: bool = False) -> None:
    folia = software == "Folia"
    require(data.get("schema") == 1 and data.get("token") == token, "Native result identity mismatch")
    require(data.get("core_source") == source and data.get("core_version") == version,
            "Loaded core identity mismatch")
    require(data.get("software") == software and data.get("minecraft") == minecraft
            and data.get("server_version", "").startswith(f"{minecraft}-{build}-")
            and data.get("folia") is folia, "Native platform mismatch")
    require(data.get("assertions") == (27 if folia else 26), "Native assertions did not complete")
    require(data.get("active_handles") == 0 and set(data.get("cases", {})) == CASES,
            "Native lifecycle evidence is incomplete")
    if folia:
        require(data.get("native_removed_entity_rejected") is True, "Native rejection control did not execute")
    if expected_failure:
        require(folia and data.get("status") == "FAIL"
                and sorted(data.get("failures", [])) == REJECTION_FAILURES,
                "The expected baseline defect was not reproduced exactly")
    else:
        require(data.get("status") == "PASS" and data.get("failures") == [], "Native lifecycle regression failed")
    for name, case in data["cases"].items():
        cancelled = name == "explicitly_cancelled"
        retired = folia and (name.startswith("rejected_") or name == "retired_after_acceptance")
        expected_retired = 0 if expected_failure and name.startswith("rejected_") else int(retired)
        require(case.get("work") == int(not retired and not cancelled)
                and case.get("retired") == expected_retired
                and case.get("cancelled") is (retired or cancelled), "Native case counters mismatch: " + name)
        if name.startswith("live_"):
            require(case.get("owned") == 1, "Native work ran outside its owner: " + name)


def validate_completion(receipt: dict, token: str, exit_code: int) -> None:
    require(exit_code == 0 and receipt.get("token") == token and receipt.get("server_stopping") is True,
            "Missing or abnormal native shutdown completion")


def prepare_cache(server: Path, work: Path, cache: Path | None) -> None:
    if cache is None:
        return
    with zipfile.ZipFile(server) as jar:
        expected, url, filename = jar.read("META-INF/download-context").decode("utf-8").strip().split("\t")
    require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None and Path(filename).name == filename,
            "Invalid native launcher cache contract")
    source = cache / filename
    require(source.is_file() and not source.is_symlink() and digest(source) == expected,
            "Native launcher cache checksum mismatch")
    (work / "cache").mkdir()
    shutil.copy2(source, work / "cache" / filename)


def compile_probe(java_home: Path, work: Path, core: Path) -> Path:
    jars = [core, *sorted((work / "libraries").rglob("*.jar")), *sorted((work / "versions").rglob("*.jar"))]
    require(len(jars) > 2, "Native server classpath is incomplete")
    classes = work / "probe-classes"
    classes.mkdir()
    result = subprocess.run([str(java_home / "bin" / "javac"), "--release", "21", "-encoding", "UTF-8",
                             "-cp", os.pathsep.join(map(str, jars)), "-d", str(classes),
                             str(HERE / "NativeEntityRetirementProbe.java")],
                            capture_output=True, text=True, timeout=120)
    (work / "compile.log").write_text(result.stdout + result.stderr)
    require(result.returncode == 0, "Native probe compilation failed; inspect compile.log")
    target = work / "plugins" / "RetirementProbe.jar"
    descriptor = """name: RetirementProbe
version: 1.0.0
main: io.github.wickidcow.validation.NativeEntityRetirementProbe
api-version: 1.21.11
folia-supported: true
depend: [Slimefun]
commands:
  retirementprobe:
    description: Disposable native entity retirement regression
"""
    entries = {"plugin.yml": descriptor.encode("utf-8")}
    entries.update({path.relative_to(classes).as_posix(): path.read_bytes() for path in classes.rglob("*.class")})
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as jar:
        for name, content in sorted(entries.items()):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            jar.writestr(entry, content)
    return target


def stop(process: subprocess.Popen) -> None:
    timed_out = False
    if process.poll() is None:
        try:
            process.stdin.write("stop\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    process.stdin.close()
    require(not timed_out, "Native shutdown timed out and required forced termination")


def read_native_output(native_log: Path, console: Path) -> str:
    native = native_log.read_text(errors="replace") if native_log.is_file() else ""
    captured = console.read_text(errors="replace")
    require(not any(marker in output for output in (native, captured) for marker in BAD_LOG_MARKERS),
            "Native lifecycle probe failed")
    return native


def wait_for_startup(process: subprocess.Popen, native_log: Path, console: Path, timeout: float = 240) -> None:
    deadline = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < deadline:
        if "Done (" in read_native_output(native_log, console):
            require(process.poll() is None and time.monotonic() < deadline,
                    "Native startup completed after the deadline or server exit")
            return
        time.sleep(0.25)
    raise RuntimeError("Native server startup did not complete")


def wait_for_result(process: subprocess.Popen, native_log: Path, console: Path,
                    evidence: Path, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < deadline:
        output = read_native_output(native_log, console)
        completion_logged = "RETIREMENT_PROBE PASS" in output or "RETIREMENT_PROBE FAIL" in output
        if evidence.is_file() and completion_logged:
            require(process.poll() is None and time.monotonic() < deadline,
                    "Native completion arrived after the deadline or server exit")
            return
        time.sleep(0.2)
    raise RuntimeError("Native lifecycle probe did not complete")


def run(args: argparse.Namespace) -> dict:
    core = args.core.absolute()
    metadata = json.loads(args.core_metadata.read_text())
    version = validate_core(core, metadata, args.expected_source)
    server = args.server_jar.absolute()
    require(server.is_file() and not server.is_symlink()
            and re.fullmatch(r"[0-9a-f]{64}", args.server_sha256) is not None
            and digest(server) == args.server_sha256, "Native server checksum mismatch")
    require(not args.expect_missing_retirement or args.software == "Folia", "Baseline failure is Folia-only")
    work = args.work_dir.absolute()
    require(not work.exists() and not work.is_symlink() and work.parent.is_dir(),
            "Refusing an existing fixture or missing parent directory")
    java = args.java_home / "bin" / "java"
    require(java.is_file() and (args.java_home / "bin" / "javac").is_file(), "A full native JDK is required")
    work.mkdir()
    (work / "plugins").mkdir()
    shutil.copy2(server, work / "server.jar")
    installed_core = work / "plugins" / "Slimefun-Legacy-retirement.jar"
    shutil.copy2(core, installed_core)
    prepare_cache(server, work, args.server_cache)
    with (work / "bootstrap.log").open("w") as log:
        initialized = subprocess.run([str(java), "-jar", "server.jar", "--version"], cwd=work,
                                     stdout=log, stderr=subprocess.STDOUT, timeout=240)
    require(initialized.returncode == 0, "Native launcher initialization failed; inspect bootstrap.log")
    probe = compile_probe(args.java_home, work, installed_core)
    (work / "eula.txt").write_text("eula=true\n")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    settings = {"server-ip": "127.0.0.1", "server-port": port, "online-mode": "false",
                "level-name": "retirement-probe-world", "level-type": "minecraft:flat",
                "generator-settings": '{"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:stone","height":2},{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains","structures":{}}',
                "view-distance": 2, "simulation-distance": 2, "spawn-protection": 0,
                "enable-rcon": "false", "enable-query": "false", "max-players": 1,
                "pause-when-empty-seconds": -1, "motd": "Disposable entity retirement regression"}
    (work / "server.properties").write_text("".join(f"{key}={value}\n" for key, value in settings.items()))
    (work / "bukkit.yml").write_text("settings:\n  allow-end: false\n")
    token = str(uuid.uuid4())
    arguments = {"token": token, "source": args.expected_source, "version": version,
                 "software": args.software, "minecraft": args.minecraft, "build": args.build}
    command = [str(java), "-Xms256M", "-Xmx768M", "-Dterminal.jline=false", "-Dterminal.ansi=false",
               *[f"-Dsfl.native.retirement.{key}={value}" for key, value in arguments.items()],
               "-jar", "server.jar", "--nogui"]
    console = work / "console.log"
    native_log = work / "logs" / "latest.log"
    # Launcher initialization may log, but it is not evidence for this boot.
    native_log.unlink(missing_ok=True)
    evidence = work / "plugins" / PLUGIN / "result.json"
    with console.open("w") as log:
        process = subprocess.Popen(command, cwd=work, stdin=subprocess.PIPE, stdout=log,
                                   stderr=subprocess.STDOUT, text=True)
        try:
            wait_for_startup(process, native_log, console)
            process.stdin.write("retirementprobe\n")
            process.stdin.flush()
            wait_for_result(process, native_log, console, evidence)
        finally:
            stop(process)
    data = json.loads(evidence.read_text())
    validate_result(data, source=args.expected_source, version=version, software=args.software,
                    minecraft=args.minecraft, build=args.build, token=token,
                    expected_failure=args.expect_missing_retirement)
    shutdown_path = work / "plugins" / PLUGIN / "normal-shutdown.json"
    completion = json.loads(shutdown_path.read_text())
    validate_completion(completion, token, process.returncode)
    output = read_native_output(native_log, console)
    require("RETIREMENT_PROBE " + data["status"] in output, "Native file log evidence mismatch")
    require(digest(installed_core) == metadata["core_sha256"]
            and digest(work / "server.jar") == args.server_sha256, "Native artifact changed during execution")
    return {"schema": 1, "status": "EXPECTED_BASELINE_FAILURE" if args.expect_missing_retirement else "PASS",
            "source_commit": args.expected_source, "core_sha256": metadata["core_sha256"], "core_version": version,
            "server_sha256": args.server_sha256, "probe_sha256": digest(probe), "native": data,
            "normal_shutdown_exit_code": process.returncode, "normal_shutdown": completion,
            "console_sha256": digest(console), "native_log_sha256": digest(native_log),
            "native_result_sha256": digest(evidence),
            "normal_shutdown_sha256": digest(shutdown_path),
            "limits": "Synthetic entity lifecycle on exact native builds; not client inventory, cross-region transport, or addon gameplay certification."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--core-metadata", type=Path, required=True)
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--server-jar", type=Path, required=True)
    parser.add_argument("--server-sha256", required=True)
    parser.add_argument("--server-cache", type=Path)
    parser.add_argument("--java-home", type=Path, default=Path(os.environ.get("JAVA_HOME", "")))
    parser.add_argument("--software", choices=("Folia", "Purpur"), required=True)
    parser.add_argument("--minecraft", choices=("26.3",), required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--allow-disposable-writes", action="store_true", required=True)
    parser.add_argument("--expect-missing-retirement", action="store_true")
    args = parser.parse_args()
    require(re.fullmatch(r"[1-9][0-9]*", args.build) is not None, "Native build must be a positive integer")
    report = run(args)
    (args.work_dir / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
