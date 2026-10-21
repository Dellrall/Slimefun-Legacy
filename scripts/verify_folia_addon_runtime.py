#!/usr/bin/env python3
"""Verify the exact declared-addon selection, installed bytes and startup log."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


COMMIT_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
CORE_JAR_NAME = "Slimefun-Legacy-smoke.jar"
LOG_PREFIX_RE = re.compile(r"^\[[^\]\n]+\](?:\s+\[[^\]\n]+\])?:\s*")


def unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate runtime selection field: {key}")
        result[key] = value
    return result


def valid_name(value: object, label: str, *, jar: bool = False) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError(f"Invalid {label}: {value!r}")
    if jar and ("/" in value or "\\" in value or not value.endswith(".jar")):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def expected_plugins(expected_file: Path) -> list[tuple[str, str]]:
    rows = []
    jars = set()
    plugins = set()
    for line in expected_file.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) != 2:
            raise ValueError("Expected addon list requires exactly one JAR/plugin pair per line")
        jar = valid_name(fields[0], "expected addon JAR name", jar=True)
        plugin = valid_name(fields[1], "expected addon plugin name")
        if jar.casefold() in jars or plugin.casefold() in plugins:
            raise ValueError("Expected addon list contains duplicate JAR/plugin names")
        if jar.casefold() == CORE_JAR_NAME.casefold() or plugin.casefold() == "slimefun":
            raise ValueError("Expected addon conflicts with the installed Slimefun core")
        jars.add(jar.casefold())
        plugins.add(plugin.casefold())
        rows.append((jar, plugin))
    if not rows:
        raise ValueError("Expected addon list is empty")
    return rows


def verified_selection(selection_file: Path, expected_file: Path, expected_source: str) -> dict:
    if not COMMIT_RE.fullmatch(expected_source):
        raise ValueError("Expected core source must be a full commit hash")
    selection = json.loads(selection_file.read_text(encoding="utf-8"), object_pairs_hook=unique_json_object)
    if (not isinstance(selection, dict) or type(selection.get("schema")) is not int
            or selection["schema"] != 1
            or selection.get("scope") != "folia-declared-startup-runtime-selection"):
        raise ValueError("Unsupported Folia runtime selection")
    if selection.get("core_source_commit") != expected_source:
        raise ValueError("Runtime addon selection belongs to a different core checkout")
    digest = selection.get("bundle_sha256")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise ValueError("Runtime addon selection is missing its canonical bundle digest")
    rows = selection.get("addons")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Runtime addon selection is empty")
    if type(selection.get("addon_count")) is not int or selection["addon_count"] != len(rows):
        raise ValueError("Runtime addon selection count differs from its addon rows")

    selected = []
    jars = set()
    plugins = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Runtime addon selection row must be an object")
        jar = valid_name(row.get("jar"), "selected addon JAR name", jar=True)
        plugin = valid_name(row.get("plugin"), "selected addon plugin name")
        if jar.casefold() in jars or plugin.casefold() in plugins:
            raise ValueError("Runtime selection contains duplicate JAR/plugin names")
        digest = row.get("jar_sha256")
        commit = row.get("commit")
        if (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)
                or not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit)):
            raise ValueError(f"Runtime selection is missing source/hash evidence: {jar}")
        jars.add(jar.casefold())
        plugins.add(plugin.casefold())
        selected.append((jar, plugin))

    expected = expected_plugins(expected_file)
    if set(selected) != set(expected):
        raise ValueError("Expected addon JAR/plugin pairs differ from the exact runtime selection")
    return selection


def verify_jars(selection: dict, directory: Path, core_jar: Path | None = None) -> dict:
    wanted = {row["jar"] for row in selection["addons"]}
    if core_jar is not None:
        wanted.add(CORE_JAR_NAME)
    actual = {path.name for path in directory.iterdir() if path.name.casefold().endswith(".jar")}
    if actual != wanted:
        raise ValueError(f"Runtime JAR set differs from selection: expected={sorted(wanted)!r}, actual={sorted(actual)!r}")
    for row in selection["addons"]:
        path = directory / row["jar"]
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Runtime addon must be a regular JAR file: {row['jar']}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["jar_sha256"]:
            raise ValueError(f"Runtime addon digest mismatch: {row['jar']}")

    receipt = {
        "schema": 1,
        "core_source_commit": selection["core_source_commit"],
        "bundle_sha256": selection["bundle_sha256"],
        "bundle_revision": selection.get("bundle_revision"),
        "addon_count": len(selection["addons"]),
        "addons": selection["addons"],
    }
    if core_jar is not None:
        installed = directory / CORE_JAR_NAME
        if not installed.is_file() or installed.is_symlink():
            raise ValueError("Installed core must be a regular JAR file")
        original_bytes = core_jar.read_bytes()
        if not original_bytes or installed.read_bytes() != original_bytes:
            raise ValueError("Installed core JAR bytes differ from the supplied candidate")
        receipt["core_jar"] = CORE_JAR_NAME
        receipt["core_jar_sha256"] = hashlib.sha256(original_bytes).hexdigest()
    return receipt


def verify_log(log_file: Path, expected_file: Path) -> None:
    expected = expected_plugins(expected_file)
    messages = [LOG_PREFIX_RE.sub("", line).strip() for line in log_file.read_text(encoding="utf-8").splitlines()]
    try:
        shutdown = messages.index("Stopping server")
    except ValueError as exc:
        raise ValueError("Runtime log has no normal server shutdown boundary") from exc
    active = messages[:shutdown]
    if not any(message.startswith("Done (") for message in active):
        raise ValueError("Runtime log has no completed startup before shutdown")
    for jar, plugin in expected:
        enable = re.compile(r"^(?:\[" + re.escape(plugin) + r"\]\s+)?Enabling " + re.escape(plugin) + r" v\S")
        disable = re.compile(r"^(?:\[" + re.escape(plugin) + r"\]\s+)?Disabling " + re.escape(plugin) + r" v\S")
        if not any(enable.search(message) for message in active):
            raise ValueError(f"Expected admitted addon did not enable before shutdown: {plugin} ({jar})")
        if any(disable.search(message) for message in active):
            raise ValueError(f"Admitted addon disabled before normal server shutdown: {plugin} ({jar})")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("selection", "installed"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--selection", type=Path, required=True)
        sub.add_argument("--expected-file", type=Path, required=True)
        sub.add_argument("--plugin-dir", type=Path, required=True)
        sub.add_argument("--expect-source", required=True)
        if command == "installed":
            sub.add_argument("--core-jar", type=Path, required=True)
            sub.add_argument("--receipt", type=Path)
    log = subparsers.add_parser("log")
    log.add_argument("--console-log", type=Path, required=True)
    log.add_argument("--expected-file", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "log":
            verify_log(args.console_log, args.expected_file)
        else:
            selection = verified_selection(args.selection, args.expected_file, args.expect_source)
            receipt = verify_jars(selection, args.plugin_dir, getattr(args, "core_jar", None))
            if getattr(args, "receipt", None) is not None:
                args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("Verified", receipt["addon_count"], "exact declared-Folia addon JARs.")
    except (OSError, ValueError, KeyError) as exc:
        print(f"Folia addon runtime verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
