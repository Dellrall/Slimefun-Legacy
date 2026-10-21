#!/usr/bin/env python3
"""Prepare the exact Folia-declared addon subset for runtime startup validation."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile

import yaml


SHA256_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def string_list(value: object, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        values = value
    else:
        raise ValueError(f"{label} must be a string or list of strings")
    cleaned = [item.strip() for item in values if item.strip()]
    if len(cleaned) != len({item.casefold() for item in cleaned}):
        raise ValueError(f"{label} contains duplicate plugin names")
    return cleaned


def prepare(
    bundle_path: Path,
    report_path: Path,
    output_dir: Path,
    expected_file: Path,
    selection_output: Path,
    expected_source: str | None = None,
) -> dict:
    report = load_json(report_path)
    if report.get("schema") != 1 or report.get("scope") != "descriptor-admission-only":
        raise ValueError("Unsupported Folia admission report")
    source = report.get("core_source_commit")
    if not isinstance(source, str) or not COMMIT_RE.fullmatch(source):
        raise ValueError("Admission report is missing a full core source commit")
    if expected_source is not None and source != expected_source:
        raise ValueError("Admission report belongs to a different core checkout")

    raw_bundle = bundle_path.read_bytes()
    bundle_digest = sha256(raw_bundle)
    if report.get("bundle_sha256") != bundle_digest:
        raise ValueError("Canonical bundle bytes differ from the audited bundle")

    rows = report.get("addons")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Admission report contains no addon rows")
    selected = [row for row in rows if isinstance(row, dict) and row.get("admission") == "declared-true"]
    expected_count = report.get("counts", {}).get("declared_true")
    if not isinstance(expected_count, int) or expected_count <= 0 or len(selected) != expected_count:
        raise ValueError("Declared-true addon count does not match the admission report")

    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.jar"):
        old.unlink()

    prepared: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(raw_bundle)) as bundle:
        names = set(bundle.namelist())
        for row in selected:
            jar_name = row.get("jar")
            jar_digest = row.get("jar_sha256")
            descriptor_name = row.get("descriptor")
            repository = row.get("repository")
            commit = row.get("commit")
            if (
                not isinstance(jar_name, str)
                or Path(jar_name).name != jar_name
                or not jar_name.endswith(".jar")
                or jar_name not in names
                or not isinstance(jar_digest, str)
                or not SHA256_RE.fullmatch(jar_digest)
                or not isinstance(descriptor_name, str)
                or not isinstance(repository, str)
                or not isinstance(commit, str)
                or not COMMIT_RE.fullmatch(commit)
            ):
                raise ValueError(f"Invalid declared-true admission row: {row!r}")

            jar_bytes = bundle.read(jar_name)
            if sha256(jar_bytes) != jar_digest:
                raise ValueError(f"Declared addon JAR hash changed after admission: {jar_name}")

            with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jar:
                if descriptor_name not in jar.namelist():
                    raise ValueError(f"Audited descriptor is missing from {jar_name}")
                descriptor = yaml.safe_load(jar.read(descriptor_name).decode("utf-8-sig")) or {}
                if not isinstance(descriptor, dict):
                    raise ValueError(f"Plugin descriptor is not a mapping: {jar_name}")
                if descriptor.get("folia-supported") is not True:
                    raise ValueError(f"Runtime-selected addon no longer explicitly declares Folia support: {jar_name}")
                plugin_name = descriptor.get("name")
                if not isinstance(plugin_name, str) or not plugin_name.strip():
                    raise ValueError(f"Runtime-selected addon has no plugin name: {jar_name}")
                dependencies = string_list(descriptor.get("depend"), f"{jar_name} depend")

            target = output_dir / jar_name
            target.write_bytes(jar_bytes)
            prepared.append(
                {
                    "repository": repository,
                    "commit": commit,
                    "jar": jar_name,
                    "jar_sha256": jar_digest,
                    "plugin": plugin_name.strip(),
                    "depend": dependencies,
                }
            )

    plugin_names = {row["plugin"].casefold() for row in prepared}
    if len(plugin_names) != len(prepared):
        raise ValueError("Declared Folia subset contains duplicate plugin names")
    available = {"slimefun"} | plugin_names
    for row in prepared:
        missing = [dep for dep in row["depend"] if dep.casefold() not in available]
        if missing:
            raise ValueError(
                f"Runtime-selected addon {row['plugin']} has unavailable hard dependencies: {', '.join(missing)}"
            )

    prepared.sort(key=lambda row: row["plugin"].casefold())
    expected_file.parent.mkdir(parents=True, exist_ok=True)
    expected_file.write_text(
        "".join(f"{row['jar']}\t{row['plugin']}\n" for row in prepared),
        encoding="utf-8",
    )

    result = {
        "schema": 1,
        "scope": "folia-declared-startup-runtime-selection",
        "bundle": bundle_path.name,
        "bundle_sha256": bundle_digest,
        "bundle_revision": report.get("bundle_revision"),
        "core_source_commit": source,
        "addon_count": len(prepared),
        "addons": prepared,
        "limits": [
            "startup admission is not gameplay or concurrency certification",
            "only explicit folia-supported true addons are included",
            "soft dependencies are intentionally not required by this startup lane",
        ],
    }
    selection_output.parent.mkdir(parents=True, exist_ok=True)
    selection_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("admission_report", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-file", type=Path, required=True)
    parser.add_argument("--selection-output", type=Path, required=True)
    parser.add_argument("--expect-source")
    args = parser.parse_args()

    try:
        result = prepare(
            args.bundle,
            args.admission_report,
            args.output_dir,
            args.expected_file,
            args.selection_output,
            args.expect_source,
        )
    except Exception as exc:
        print(f"Folia addon runtime selection failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
