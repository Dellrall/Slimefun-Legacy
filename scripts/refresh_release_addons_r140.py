#!/usr/bin/env python3
"""Build deterministic r140 from the exact published r137 ZIP with only Networks and IE2 replaced."""
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


def manifest(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("SF_ADDON_MANIFEST.json"))


def build(config: dict, matrix: dict, original: Path, jar_dir: Path, output: Path, work: Path) -> dict:
    require(config["bundle_revision"] == matrix["bundle_revision"] == 140, "Expected r140")
    require(config["input_bundle_revision"] == 137, "Expected published r137 input")
    require(len(matrix["addons"]) == config["expected_addons"] == 45, "Addon roster changed")
    require(matrix["bundle_name"] == config["output_name"], "Matrix/output filename mismatch")
    require(digest(original) == config["published_old_bundle_sha256"],
            "Published r137 ZIP changed; rebase instead of overwriting")
    validate_bundle(original)
    before = manifest(original)
    require(before.get("bundle_revision") == 137, "Input manifest is not r137")
    require(before.get("core_source_commit") == config["core_source_commit"], "Core provenance changed")
    require(len(before.get("addons", [])) == 45, "Input addon count changed")

    old_rows = {row["repository"]: row for row in before["addons"]}
    locked = {row["repository"]: row["source_commit"] for row in matrix["addons"]}
    replacements = config["replacements"]
    require([r["repository"] for r in replacements] ==
            ["wickidcow/SF_NetworksExp", "wickidcow/SF_InfinityExpansion2"],
            "Unexpected r140 replacement order")
    changing = {r["repository"] for r in replacements}
    require(len(changing) == 2, "Expected exactly two changed addons")

    for item in replacements:
        old = old_rows.get(item["repository"])
        require(old is not None, "Missing old addon row: " + item["repository"])
        require(old["commit"] == item["old_commit"], "Old source changed: " + item["repository"])
        require(locked[item["repository"]] == item["new_commit"], "New source not pinned")
        jar = jar_dir / item["new_jar"]
        require(jar.is_file() and digest(jar) == item["new_sha256"],
                "Released JAR digest mismatch: " + item["new_jar"])

    require(all(locked[repo] == row["commit"] for repo, row in old_rows.items()
                if repo not in changing), "A source pin outside Networks/IE2 changed")

    work.mkdir(parents=True, exist_ok=True)
    current = original
    reports = []
    stage_outputs = []

    for index, item in enumerate(replacements):
        stage_matrix = copy.deepcopy(matrix)
        # Future replacements must remain on their published-r137 source until their stage.
        future = {r["repository"]: r["old_commit"] for r in replacements[index + 1:]}
        for addon in stage_matrix["addons"]:
            if addon["repository"] in future:
                addon["source_commit"] = future[addon["repository"]]

        old = manifest(current)
        old_row = next(r for r in old["addons"] if r["repository"] == item["repository"])
        stage_config = {
            "release_tag": config["release_tag"],
            "core_source_commit": config["core_source_commit"],
            "expected_addons": config["expected_addons"],
            "bundle_revision": config["bundle_revision"],
            **item,
            "old_bundle_sha256": digest(current),
            "old_jar": old_row["jar"],
        }
        destination = output if index == len(replacements) - 1 else work / f"stage-{index + 1}.zip"
        report = refresh(stage_config, stage_matrix, current, jar_dir / item["new_jar"], destination)
        require(report["addon_count"] == 45 and report["unchanged_addons"] == 44,
                "Each stage must replace exactly one addon JAR")
        reports.append({**report, "repository": item["repository"], "old_jar": old_row["jar"]})
        stage_outputs.append(destination)
        (work / f"stage-{index + 1}-report.json").write_text(json.dumps(reports[-1], indent=2) + "\n")
        current = destination

    validate_bundle(output)
    after = manifest(output)
    require(after["bundle_revision"] == 140, "Final manifest revision mismatch")
    require({row["repository"]: row["commit"] for row in after["addons"]} == locked,
            "Final manifest source pins differ from matrix")

    with zipfile.ZipFile(original) as older, zipfile.ZipFile(output) as newer:
        old_jars = {n for n in older.namelist() if n.endswith(".jar")}
        new_jars = {n for n in newer.namelist() if n.endswith(".jar")}
        removed = {next(r for r in before["addons"] if r["repository"] == item["repository"])["jar"]
                   for item in replacements}
        added = {item["new_jar"] for item in replacements}
        require(len(old_jars) == len(new_jars) == 45, "Addon count changed")
        require(new_jars == (old_jars - removed) | added, "Unexpected JAR set change")
        unchanged = old_jars - removed
        require(len(unchanged) == 43, "Expected 43 unchanged JARs")
        require(all(older.read(name) == newer.read(name) for name in unchanged),
                "An unrelated addon JAR changed")
        for item in replacements:
            require(newer.read(item["new_jar"]) == (jar_dir / item["new_jar"]).read_bytes(),
                    "Bundled JAR differs from public release: " + item["new_jar"])
        metadata = {"SF_ADDON_MANIFEST.json", "SHA256SUMS.txt", "COMPATIBILITY.txt"}
        unchanged_other = set(older.namelist()) - old_jars - metadata
        require(all(older.read(name) == newer.read(name) for name in unchanged_other),
                "An unrelated non-addon ZIP member changed")

    # Re-run the final stage from the exact first-stage bytes and require deterministic output.
    first_stage = stage_outputs[0]
    final_item = replacements[-1]
    first_manifest = manifest(first_stage)
    final_old_row = next(r for r in first_manifest["addons"] if r["repository"] == final_item["repository"])
    final_config = {
        "release_tag": config["release_tag"],
        "core_source_commit": config["core_source_commit"],
        "expected_addons": config["expected_addons"],
        "bundle_revision": config["bundle_revision"],
        **final_item,
        "old_bundle_sha256": digest(first_stage),
        "old_jar": final_old_row["jar"],
    }
    repeated = work / "repeated-final.zip"
    refresh(final_config, matrix, first_stage, jar_dir / final_item["new_jar"], repeated)
    require(digest(repeated) == digest(output), "r140 output is not deterministic")

    result = {
        "bundle_revision": 140,
        "bundle_name": config["output_name"],
        "bundle_sha256": digest(output),
        "previous_bundle_sha256": digest(original),
        "addon_count": 45,
        "unchanged_addons": 43,
        "changed_repositories": [r["repository"] for r in replacements],
        "stages": reports,
    }
    (work / "r140-result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "matrix", "original", "jar-dir", "output", "work-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(
        json.loads(args.config.read_text()),
        json.loads(args.matrix.read_text()),
        args.original, args.jar_dir, args.output, args.work_dir), indent=2))


if __name__ == "__main__":
    main()
