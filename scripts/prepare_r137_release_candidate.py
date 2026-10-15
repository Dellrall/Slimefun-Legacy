#!/usr/bin/env python3
"""Prepare a read-only r137 release candidate from exact published/source-CI bytes.

This command never uploads a release, edits a tag, or touches a running server.
The other 44 addon JARs and the published 4.1.74 core remain byte-identical.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile

CORE_REPO = "wickidcow/Slimefun-Legacy"
MAGIC_REPO = "wickidcow/SF_MagicExpansion"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gh_json(endpoint: str) -> dict:
    response = subprocess.run(["gh", "api", endpoint], check=True, capture_output=True, timeout=90)
    return json.loads(response.stdout)


def validate_release(release: dict, config: dict) -> None:
    require(release.get("id") == config["release_id"] and release.get("tag_name") == "v4.1.74",
            "Wrong baseline release")
    require(not release.get("draft") and not release.get("prerelease"), "Baseline is not a stable publication")
    require(release.get("target_commitish") == config["core_source_commit"], "Published core source changed")
    rows = release.get("assets", [])
    require(len(rows) == len(config["baseline_assets"]), "Published asset roster changed")
    actual = {r["name"]: r for r in rows}
    require(len(actual) == len(rows), "Duplicate published asset names")
    require(set(actual) == set(config["baseline_assets"]), "Published asset names changed")
    for name, expected in config["baseline_assets"].items():
        row = actual[name]
        require(row.get("id") == expected["id"] and row.get("size") == expected["size"]
                and row.get("digest") == "sha256:" + expected["sha256"]
                and row.get("state") == "uploaded", "Published asset lease changed: " + name)


def validate_source_run(run: dict, config: dict) -> None:
    require(run.get("id") == config["source_run_id"] and run.get("head_sha") == config["new_commit"],
            "Source run is not the exact reviewed MagicExpansion head")
    require(run.get("status") == "completed" and run.get("conclusion") == "success", "Source CI is not green")
    require(run.get("path") == ".github/workflows/build.yml", "Wrong source workflow")
    require(run.get("event") in ("push", "pull_request"), "Unexpected source run trigger")
    require(run.get("repository", {}).get("full_name") == MAGIC_REPO, "Wrong source repository")


def validate_artifact(artifact: dict, config: dict, name: str, expected: dict) -> None:
    require(artifact.get("id") == expected["id"] and artifact.get("name") == name,
            "Artifact identity changed")
    require(not artifact.get("expired") and artifact.get("digest") == "sha256:" + expected["sha256"],
            "Artifact is expired or its digest changed")
    run = artifact.get("workflow_run", {})
    require(run.get("id") == config["source_run_id"] and run.get("head_sha") == config["new_commit"],
            "Artifact came from a different source run")


def inspect_unit_reports(data: bytes) -> dict:
    counts = dict(tests=0, failures=0, errors=0, skipped=0)
    suites = 0
    cases = 0
    black_market = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), "Duplicate test-report entries")
        for name in archive.namelist():
            if not (name.endswith(".xml") and Path(name).name.startswith("TEST-")):
                continue
            suite = ET.fromstring(archive.read(name))
            require(suite.tag == "testsuite", "Unexpected Surefire report")
            suites += 1
            for key in counts:
                counts[key] += int(suite.attrib.get(key, 0))
            actual = suite.findall("testcase")
            cases += len(actual)
            require(not any(case.find(tag) is not None for case in actual for tag in ("failure", "error", "skipped")),
                    "Failed or skipped test case in source evidence")
            if "BlackMarket" in suite.attrib.get("name", ""):
                black_market += len(actual)
    require(suites == 14 and cases == counts["tests"] == 146 and black_market == 40,
            "Source test coverage/count changed; review rather than silently accepting it")
    require(counts["failures"] == counts["errors"] == counts["skipped"] == 0, "Source tests did not all pass")
    return {**counts, "suites": suites, "black_market_tests": black_market}


def download_artifact(config: dict, name: str, expected: dict, output: Path) -> Path:
    meta = gh_json(f"repos/{MAGIC_REPO}/actions/artifacts/{expected['id']}")
    validate_artifact(meta, config, name, expected)
    with output.open("xb") as stream:
        subprocess.run(["gh", "api", f"repos/{MAGIC_REPO}/actions/artifacts/{expected['id']}/zip"],
                       stdout=stream, check=True, timeout=180)
    require(sha256(output) == expected["sha256"], "Downloaded source artifact checksum mismatch")
    return output


def prepare(config: dict, matrix: dict, output: Path) -> dict:
    require(not output.exists(), "Refusing to reuse an existing candidate directory")
    release = gh_json(f"repos/{CORE_REPO}/releases/tags/v4.1.74")
    validate_release(release, config)
    run = gh_json(f"repos/{MAGIC_REPO}/actions/runs/{config['source_run_id']}")
    validate_source_run(run, config)
    output.mkdir(parents=True)
    original = output / "baseline"
    original.mkdir()
    for name in ("SF_Addons_1.21.11-26.3.zip", "Slimefun-Legacy4.1.74.jar"):
        subprocess.run(["gh", "release", "download", "v4.1.74", "--repo", CORE_REPO,
                        "--pattern", name, "--dir", str(original)], check=True, timeout=180)
        require(sha256(original / name) == config["baseline_assets"][name]["sha256"],
                "Published download checksum mismatch: " + name)
    reports = download_artifact(config, "magicexpansion-unit-tests", config["test_artifact"],
                                output / "source-unit-tests.zip")
    tests = inspect_unit_reports(reports.read_bytes())
    jar = download_artifact(config, config["new_jar"], config["jar_artifact"], output / config["new_jar"])
    # The source workflow explicitly uses archive:false: this payload must itself be the raw JAR.
    with zipfile.ZipFile(jar) as archive:
        require("plugin.yml" in archive.namelist(), "Source artifact was wrapped instead of a raw JAR")
    from refresh_release_addon import refresh
    candidate = output / "SF_Addons_1.21.11-26.3.zip"
    result = refresh(config, matrix, original / candidate.name, jar, candidate)
    repeat = output / "deterministic-repeat.zip"
    refresh(config, matrix, original / candidate.name, jar, repeat)
    require(candidate.read_bytes() == repeat.read_bytes(), "Targeted ZIP preparation was not deterministic")
    repeat.unlink()
    core = output / "Slimefun-Legacy-full-stack.jar"
    core.write_bytes((original / "Slimefun-Legacy4.1.74.jar").read_bytes())
    require(result["unchanged_addons"] == 44, "The other 44 addons were not retained exactly")
    validate_release(gh_json(f"repos/{CORE_REPO}/releases/tags/v4.1.74"), config)
    result.update(state="UNRELEASED_CANDIDATE", source_run_id=config["source_run_id"],
                  magic_source_commit=config["new_commit"], source_tests=tests,
                  published_core_sha256=sha256(core), release_assets_unchanged=True,
                  artifact_policy="Publish these exact tested bytes; any rebuilt JAR needs renewed verification.")
    (output / "release-readiness.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(json.loads(args.config.read_text()), json.loads(args.matrix.read_text()), args.output)


if __name__ == "__main__":
    main()
