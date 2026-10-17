#!/usr/bin/env python3
"""Audit canonical Slimefun addon JAR descriptors for Folia admission metadata.

This is an admission audit only. A declaration of folia-supported: true is not
runtime/gameplay certification, and a missing declaration is not proof of a bug.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

DESCRIPTORS = ("paper-plugin.yml", "paper-plugin.yaml", "plugin.yml", "plugin.yaml")
FOLIA_RE = re.compile(r"(?im)^\s*folia-supported\s*:\s*(true|false)\s*$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit(bundle_path: Path) -> dict:
    raw = bundle_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Bundle contains duplicate ZIP entries")
        if "SF_ADDON_MANIFEST.json" not in names:
            raise ValueError("Bundle is missing SF_ADDON_MANIFEST.json")

        manifest = json.loads(bundle.read("SF_ADDON_MANIFEST.json"))
        rows = manifest.get("addons")
        if not isinstance(rows, list) or not rows:
            raise ValueError("Manifest contains no addon records")

        manifest_jars = [str(row.get("jar", "")).strip() for row in rows]
        if len(manifest_jars) != len(set(manifest_jars)):
            raise ValueError("Manifest contains duplicate addon JAR names")

        actual_jars = sorted(name for name in names if name.endswith(".jar") and "/" not in name)
        if sorted(manifest_jars) != actual_jars:
            raise ValueError(
                f"Bundle/manifest JAR mismatch: manifest={sorted(manifest_jars)!r}, actual={actual_jars!r}"
            )

        results = []
        for row in rows:
            jar_name = str(row.get("jar", "")).strip()
            repository = str(row.get("repository", "")).strip()
            commit = str(row.get("commit", "")).strip()
            if not repository or not jar_name:
                raise ValueError(f"Invalid addon manifest row: {row!r}")

            jar_bytes = bundle.read(jar_name)
            with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jar:
                descriptor_name = next((name for name in DESCRIPTORS if name in jar.namelist()), None)
                if descriptor_name is None:
                    raise ValueError(f"No plugin descriptor in {jar_name}")
                descriptor = jar.read(descriptor_name).decode("utf-8", errors="replace")
                match = FOLIA_RE.search(descriptor)
                declared = match.group(1).lower() if match else None

            if declared == "true":
                admission = "declared-true"
            elif declared == "false":
                admission = "declared-false"
            else:
                admission = "undeclared"

            results.append(
                {
                    "repository": repository,
                    "commit": commit,
                    "jar": jar_name,
                    "jar_sha256": sha256(jar_bytes),
                    "descriptor": descriptor_name,
                    "folia_supported": declared,
                    "admission": admission,
                }
            )

    counts = {
        "declared_true": sum(row["admission"] == "declared-true" for row in results),
        "declared_false": sum(row["admission"] == "declared-false" for row in results),
        "undeclared": sum(row["admission"] == "undeclared" for row in results),
    }
    return {
        "schema": 1,
        "scope": "descriptor-admission-only",
        "bundle": bundle_path.name,
        "bundle_sha256": sha256(raw),
        "bundle_revision": manifest.get("bundle_revision"),
        "core_source_commit": manifest.get("core_source_commit"),
        "addon_count": len(results),
        "counts": counts,
        "addons": sorted(results, key=lambda row: row["repository"].casefold()),
        "limits": [
            "folia-supported true is not gameplay or concurrency certification",
            "undeclared is not proof of incompatibility",
            "this audit does not start a server or exercise region ownership",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expect-addons", type=int, default=45)
    args = parser.parse_args()

    try:
        report = audit(args.bundle)
    except Exception as exc:
        print(f"Folia addon admission audit failed: {exc}", file=sys.stderr)
        return 1

    if report["addon_count"] != args.expect_addons:
        print(
            f"Expected {args.expect_addons} addons, found {report['addon_count']}",
            file=sys.stderr,
        )
        return 1

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
