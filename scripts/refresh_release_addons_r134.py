#!/usr/bin/env python3
"""Build a deterministic three-addon r134 refresh from the exact published r133 ZIP.

This command is intentionally fail-closed: unknown source changes, a replaced
public ZIP, a mismatched release JAR, or any modified unrelated member abort.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import zipfile
from pathlib import Path

from refresh_release_addon import refresh
from verify_published_addon_bundle import validate_bundle


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("SF_ADDON_MANIFEST.json"))


def build(config: dict, matrix: dict, original: Path, jar_dir: Path,
          output: Path, working_dir: Path) -> dict:
    require(config["bundle_revision"] == matrix["bundle_revision"] == 134,
            "This workflow must stage canonical revision 134")
    require(len(matrix["addons"]) == config["expected_addons"] == 45,
            "Maintained addon roster changed")
    require(digest(original) == config["published_old_bundle_sha256"],
            "Live public bundle is different; rebase rather than overwriting")
    require(original.resolve() != output.resolve(), "Do not overwrite the published input")
    require(output.resolve() not in (jar_dir.resolve(), working_dir.resolve()),
            "Output must be a file separate from working directory")

    validate_bundle(original)
    before = read_manifest(original)
    require(before["bundle_revision"] == 133, "Input must be the published revision 133")
    require(before["core_source_commit"] == config["core_source_commit"],
            "Input core provenance changed")
    require(len(before["addons"]) == 45, "Input addon count changed")

    original_by_repo = {row["repository"]: row for row in before["addons"]}
    locked = {row["repository"]: row["source_commit"] for row in matrix["addons"]}
    require(len(original_by_repo) == len(locked) == 45, "Duplicate/missing addon repositories")

    replacements = config["replacements"]
    expected = ["networksexp", "magicexpansion", "luckyblocks"]
    require([item["slug"] for item in replacements] == expected,
            "Expected approved Networks, Magic Expansion, Lucky Blocks ordering")
    changing = {item["repository"] for item in replacements}
    require(len(changing) == 3, "Expected exactly three unique addons")

    for item in replacements:
        old = original_by_repo.get(item["repository"])
        require(old is not None, "Addon missing: " + item["repository"])
        require(old["jar"] == item["old_jar"] and old["commit"] == item["old_commit"],
                "Old addon identity changed: " + item["repository"])
        require(locked[item["repository"]] == item["new_commit"],
                "New source not pinned: " + item["repository"])
        new_jar = jar_dir / item["new_jar"]
        require(new_jar.is_file() and digest(new_jar) == item["new_sha256"],
                "New released JAR changed: " + item["new_jar"])
    require(all(locked[r] == row["commit"] for r, row in original_by_repo.items()
                if r not in changing), "A source pin outside the three approved addons changed")

    working_dir.mkdir(parents=True, exist_ok=True)
    original_path = original
    reports = []

    for i, item in enumerate(replacements):
        stage_matrix = copy.deepcopy(matrix)
        future = {row["repository"]: row["old_commit"] for row in replacements[i + 1:]}
        for addon in stage_matrix["addons"]:
            if addon["repository"] in future:
                addon["source_commit"] = future[addon["repository"]]
        stage_config = {
            **{key: config[key] for key in
               ("release_tag", "core_source_commit", "expected_addons", "bundle_revision")},
            **item,
            "old_bundle_sha256": digest(original_path),
        }
        stage_number = i + 1
        stage_matrix_path = working_dir / f"matrix-stage-{stage_number}.json"
        stage_config_path = working_dir / f"config-stage-{stage_number}.json"
        stage_matrix_path.write_text(json.dumps(stage_matrix, indent=2) + "\n")
        stage_config_path.write_text(json.dumps(stage_config, indent=2) + "\n")
        destination = output if i == len(replacements) - 1 else (
            working_dir / f"stage-{stage_number}.zip")
        report = refresh(stage_config, stage_matrix, original_path,
                         jar_dir / item["new_jar"], destination)
        require(report["addon_count"] == 45 and report["unchanged_addons"] == 44,
                "Each targeted step must change exactly one of 45 addon JARs")
        reports.append({**report, "repository": item["repository"]})
        (working_dir / f"stage-{stage_number}-validation.json").write_text(
            json.dumps(reports[-1], indent=2) + "\n")
        original_path = destination

    validate_bundle(output)
    after = read_manifest(output)
    require(after["bundle_revision"] == 134 and after["core_source_commit"] ==
            before["core_source_commit"], "Output metadata does not match r134 source")
    require({row["repository"]: row["commit"] for row in after["addons"]} == locked,
            "Final source manifest differs from the exact approved matrix")

    with zipfile.ZipFile(original) as older, zipfile.ZipFile(output) as newer:
        old_jars = {name for name in older.namelist() if name.endswith(".jar")}
        new_jars = {name for name in newer.namelist() if name.endswith(".jar")}
        require(len(old_jars) == len(new_jars) == 45, "Changed addon roster size")
        removed = {r["old_jar"] for r in replacements}
        added = {r["new_jar"] for r in replacements}
        require(new_jars == (old_jars - removed) | added,
                "Unexpected JAR filenames in replacement archive")
        unchanged = old_jars - removed
        require(len(unchanged) == 42 and all(older.read(name) == newer.read(name)
                for name in unchanged), "One of the other 42 plugin JARs was changed")
        for item in replacements:
            require(newer.read(item["new_jar"]) ==
                    (jar_dir / item["new_jar"]).read_bytes(),
                    "Bundled new JAR does not match the official release asset")
        allowed_metadata = {"SF_ADDON_MANIFEST.json", "SHA256SUMS.txt", "COMPATIBILITY.txt"}
        unchanged_other = set(older.namelist()) - old_jars - allowed_metadata
        require(all(older.read(name) == newer.read(name) for name in unchanged_other),
                "An unrelated non-addon ZIP entry was changed")

    # Re-run final stage independently and require an exact deterministic digest.
    last = replacements[-1]
    stage_previous = working_dir / "stage-2.zip"
    final_config = json.loads((working_dir / "config-stage-3.json").read_text())
    duplicate = working_dir / "repeated-final.zip"
    refresh(final_config, matrix, stage_previous, jar_dir / last["new_jar"], duplicate)
    require(digest(duplicate) == digest(output),
            "Final ZIP differs between two clean deterministic builds")
    return {
        "bundle_revision": 134,
        "bundle_sha256": digest(output),
        "previous_bundle_sha256": digest(original),
        "addon_count": 45,
        "unchanged_addons": 42,
        "changed_repositories": [r["repository"] for r in replacements],
        "stages": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "matrix", "original", "jar-dir", "output", "work-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = build(json.loads(args.config.read_text()),
                   json.loads(args.matrix.read_text()),
                   args.original, args.jar_dir, args.output, args.work_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
