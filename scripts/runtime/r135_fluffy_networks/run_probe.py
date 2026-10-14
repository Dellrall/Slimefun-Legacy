#!/usr/bin/env python3
"""Run a test-only Networks↔Fluffy integration probe on the disposable r135 Paper 26.3 full-stack directory.

The regular full-stack smoke has already booted and shut down cleanly twice.
This runner adds only a temporary test plugin, starts one more offline local Paper
process, and exercises the real registered ticker and Networks storage adapter.
It must never target an existing production Minecraft installation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
EXPECTED_VERSIONS = {
    "wickidcow/SF_FluffyMachines": ("SF_FluffyMachines26.2.16.jar", "5a41cbd4b156c560f6d35cbcffd9b8e22f026c2a"),
    "wickidcow/SF_NetworksExp": ("SF_Networks1.0.54.jar", "c2e6c6779374ade77d5e2dc07fcc60cc42f788b8"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(work: Path, bundle: Path, java: Path) -> dict | None:
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("SF_ADDON_MANIFEST.json"))
    revision = manifest.get("bundle_revision")
    if revision != 135:
        print(f"R135 native test skipped: bundle revision {revision} is not 135", flush=True)
        return None

    workspace = (Path.cwd() / "build").resolve()
    if not work.is_relative_to(workspace) or work.name != "full-stack-26.3":
        raise RuntimeError("Refusing to run outside a disposable build/full-stack-26.3 directory")
    if not (work / "smoke-result.txt").is_file() or not (work / "server.jar").is_file():
        raise RuntimeError("A passing two-boot Paper 26.3 full-stack staging directory is required")
    if "runtime smoke: PASS" not in (work / "smoke-result.txt").read_text(encoding="utf-8"):
        raise RuntimeError("Full-stack baseline did not pass before the native interoperability probe")
    if not (work / "eula.txt").is_file() or not (work / "server.properties").is_file():
        raise RuntimeError("Disposable test server fixture is incomplete")

    rows = {row["repository"]: row for row in manifest["addons"]}
    resolved = {}
    for repo, (filename, commit) in EXPECTED_VERSIONS.items():
        row = rows.get(repo)
        if not row or row.get("jar") != filename or row.get("commit") != commit:
            raise RuntimeError(f"Exact r135 addon source mismatch: {repo}")
        binary = work / "plugins" / filename
        if not binary.is_file() or sha256(binary) != row.get("sha256"):
            raise RuntimeError(f"Staged addon JAR digest mismatch: {binary}")
        resolved[repo] = {"jar": filename, "commit": commit, "sha256": sha256(binary)}

    libraries = sorted({
        jar.resolve()
        for directory in ("libraries", "versions", "plugins")
        for jar in (work / directory).rglob("*.jar")
        if ".paper-remapped" not in jar.parts
    })
    if len(libraries) < 3:
        raise RuntimeError("Paper runtime libraries and staged addon JARs are missing")

    classes = work / "native-r135-probe-classes"
    if classes.exists() or (work / "plugins" / "R135FluffyNetworksProbe.jar").exists():
        raise RuntimeError("Refusing to overwrite a prior native integration probe")
    classes.mkdir()
    javac = java.with_name("javac")
    if not javac.is_file():
        raise RuntimeError(f"Missing complete Java 25 JDK: {javac}")
    command = [str(javac), "--release", "25", "-encoding", "UTF-8",
               "-cp", os.pathsep.join(map(str, libraries)), "-d", str(classes),
               str(HERE / "R135FluffyNetworksProbe.java")]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    (work / "native-r135-compile.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("R135 native plugin did not compile; see native-r135-compile.log")

    plugin_jar = work / "plugins" / "R135FluffyNetworksProbe.jar"
    with zipfile.ZipFile(plugin_jar, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(HERE / "plugin.yml", "plugin.yml")
        for item in sorted(classes.rglob("*.class")):
            archive.write(item, item.relative_to(classes).as_posix())
    return {
        "status": "STARTED", "schema": 1, "bundle_revision": 135,
        "plugin_jar_sha256": sha256(plugin_jar), "tested_addons": resolved,
        "core_jar_sha256": sha256(work / "plugins" / "Slimefun-Legacy-full-stack.jar"),
        "paper_server_sha256": sha256(work / "server.jar"),
    }


def run(work: Path, java: Path, evidence: dict, timeout: int) -> None:
    log_file = work / "native-r135.console.log"
    result_file = work / "plugins" / "R135FluffyNetworksProbe" / "result.txt"
    if result_file.exists():
        raise RuntimeError("Stale probe evidence is forbidden")
    command = [str(java), "-Dterminal.jline=false", "-Dterminal.ansi=false",
               "-Xms768M", "-Xmx3G", "-jar", "server.jar", "--nogui"]

    with log_file.open("w", encoding="utf-8") as output:
        proc = subprocess.Popen(command, cwd=work, stdin=subprocess.PIPE,
                                stdout=output, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + timeout
            started = False
            while time.monotonic() < deadline and proc.poll() is None:
                log = log_file.read_text(encoding="utf-8", errors="replace")
                if "Done (" in log and "R135 native integration probe ready" in log:
                    started = True
                    break
                if "Error occurred while enabling" in log or "Could not load plugin" in log:
                    break
                time.sleep(1)
            if not started:
                raise RuntimeError("R135 integration plugin did not enable and start; inspect native-r135.console.log")
            assert proc.stdin is not None
            proc.stdin.write("r135probe run\n")
            proc.stdin.flush()
            while time.monotonic() < deadline and proc.poll() is None and not result_file.is_file():
                time.sleep(1)
            if not result_file.is_file():
                raise RuntimeError("R135 native integration command did not produce evidence")
            result = result_file.read_text(encoding="utf-8").splitlines()
            evidence["result"] = result[0] if result else "FAIL"
            evidence["detail"] = result[1] if len(result) > 1 else "no reason reported"
        finally:
            if proc.poll() is None:
                if proc.stdin:
                    try:
                        proc.stdin.write("stop\n")
                        proc.stdin.flush()
                    except (BrokenPipeError, OSError):
                        pass
                try:
                    proc.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=20)
            if proc.stdin:
                proc.stdin.close()

    evidence["process_exit_code"] = proc.returncode
    evidence["server_log_sha256"] = sha256(log_file)
    if proc.returncode != 0 or evidence.get("result") != "PASS":
        raise RuntimeError(f"Native Networks-Fluffy integration failed: {evidence.get('detail', 'unknown')}; see {log_file}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=420)
    args = parser.parse_args()
    work = args.runtime_dir.resolve()
    java = Path(os.environ["JAVA_HOME"]) / "bin" / "java"
    if not java.is_file():
        raise RuntimeError("The native r135 test requires a complete JDK 25")
    evidence = prepare(work, args.bundle.resolve(), java)
    if evidence is None:
        return 0
    out = work / "native-r135-result.json"
    try:
        run(work, java, evidence, args.timeout)
    except Exception as error:
        evidence["result"] = "FAIL"
        evidence["error"] = str(error)
        raise
    finally:
        out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"R135 native integration FAILED: {error}", file=sys.stderr)
        sys.exit(1)
