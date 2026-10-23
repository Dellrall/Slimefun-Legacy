#!/usr/bin/env python3
"""Copy an existing optional Geyser release ZIP as opaque, unchanged bytes.

No ZIP parsing, texture processing, mapping generation or Geyser/server configuration.
The GitHub release workflow handles downloads/uploads; this script only selects
the most recent eligible asset and verifies its exact SHA-256/size.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

GEYSER_ASSET = "SlimefunLegacyRP_GEYSER-BEDROCK.zip"
TAG_PATTERN = re.compile(r"^v([0-9]+)\.([0-9]+)\.([0-9]+)$")
DIGEST_PATTERN = re.compile(r"^sha256:([0-9a-f]{64})$")


class CarryError(ValueError):
    """Release metadata or carried bytes are not trustworthy."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CarryError(message)


def version(tag: str) -> tuple[int, int, int]:
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise CarryError("Expected stable vMAJOR.MINOR.PATCH tag")
    return tuple(int(n) for n in match.groups())


def select(releases: Any, target_tag: str) -> dict[str, Any]:
    target_version = version(target_tag)
    require(isinstance(releases, list), "Expected a GitHub releases JSON array")
    sources = []
    for release in releases:
        if not isinstance(release, dict):
            continue
        tag = release.get("tag_name")
        if not isinstance(tag, str) or TAG_PATTERN.fullmatch(tag) is None:
            continue
        if release.get("draft") is not False or release.get("prerelease") is not False:
            continue
        source_version = version(tag)
        if source_version > target_version:
            continue
        assets = release.get("assets")
        require(isinstance(assets, list), "Release missing assets array: " + tag)
        matches = [asset for asset in assets if isinstance(asset, dict)
                   and asset.get("name") == GEYSER_ASSET]
        require(len(matches) <= 1, "Duplicate Geyser pack in " + tag)
        if not matches:
            continue
        asset = matches[0]
        require(asset.get("state") == "uploaded", "Geyser pack is not fully uploaded")
        require(type(asset.get("id")) is int and asset["id"] > 0, "Invalid Geyser asset ID")
        require(type(asset.get("size")) is int and asset["size"] > 0, "Invalid Geyser asset size")
        digest = asset.get("digest")
        require(isinstance(digest, str) and DIGEST_PATTERN.fullmatch(digest) is not None,
                "Geyser pack must have SHA-256 release metadata")
        sources.append((source_version, {
            "schema": 1,
            "target_tag": target_tag,
            "source_tag": tag,
            "asset_name": GEYSER_ASSET,
            "asset_id": asset["id"],
            "size_bytes": asset["size"],
            "sha256": digest.removeprefix("sha256:"),
        }))
    require(bool(sources), "No previously published stable release has the optional Geyser ZIP")
    sources.sort(key=lambda pair: pair[0])
    return sources[-1][1]


def verified_selection(selection: Any) -> dict:
    require(isinstance(selection, dict) and selection.get("schema") == 1,
            "Missing or invalid Geyser selection receipt")
    require(selection.get("asset_name") == GEYSER_ASSET, "Unexpected Geyser filename")
    target = selection.get("target_tag")
    source = selection.get("source_tag")
    require(isinstance(target, str) and isinstance(source, str), "Missing release tags")
    require(version(source) <= version(target), "Cannot carry a future release asset backward")
    require(type(selection.get("asset_id")) is int and selection["asset_id"] > 0,
            "Invalid source asset identity")
    require(type(selection.get("size_bytes")) is int and selection["size_bytes"] > 0,
            "Invalid source asset size")
    sha = selection.get("sha256")
    require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha) is not None,
            "Missing SHA-256 selection pin")
    return selection


def verify_file(selection: Any, file: Path) -> dict:
    selection = verified_selection(selection)
    require(file.is_file() and not file.is_symlink(), "Downloaded Geyser pack is not a regular file")
    require(file.name == GEYSER_ASSET, "Downloaded Geyser asset filename changed")
    require(file.stat().st_size == selection["size_bytes"], "Carried Geyser pack size changed")
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    require(digest.hexdigest() == selection["sha256"], "Carried Geyser pack SHA-256 changed")
    return {
        "source_tag": selection["source_tag"],
        "target_tag": selection["target_tag"],
        "asset_name": GEYSER_ASSET,
        "size_bytes": selection["size_bytes"],
        "sha256": selection["sha256"],
        "bytes_carried_unchanged": True,
    }


def verify_published(selection: Any, release: Any) -> dict:
    selection = verified_selection(selection)
    require(isinstance(release, dict), "Invalid published release response")
    require(release.get("tag_name") == selection["target_tag"], "Published tag mismatch")
    require(release.get("draft") is False and release.get("prerelease") is False,
            "Target release is not published")
    assets = release.get("assets")
    require(isinstance(assets, list), "Published release has no assets array")
    matches = [asset for asset in assets if isinstance(asset, dict)
               and asset.get("name") == GEYSER_ASSET]
    require(len(matches) == 1, "Published release must contain exactly one carried Geyser ZIP")
    asset = matches[0]
    require(asset.get("state") == "uploaded", "Carried asset upload not complete")
    require(asset.get("size") == selection["size_bytes"], "Published carried pack size mismatch")
    require(asset.get("digest") == "sha256:" + selection["sha256"],
            "Published carried pack SHA-256 mismatch")
    return {"source_tag": selection["source_tag"], "target_tag": selection["target_tag"],
            "sha256": selection["sha256"], "published_unchanged": True}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    choose = sub.add_parser("select")
    choose.add_argument("--releases", type=Path, required=True)
    choose.add_argument("--target-tag", required=True)
    choose.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--selection", type=Path, required=True)
    verify.add_argument("--file", type=Path, required=True)
    published = sub.add_parser("verify-published")
    published.add_argument("--selection", type=Path, required=True)
    published.add_argument("--release-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "select":
            result = select(load(args.releases), args.target_tag)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        elif args.command == "verify":
            result = verify_file(load(args.selection), args.file)
        else:
            result = verify_published(load(args.selection), load(args.release_json))
        print(json.dumps(result, indent=2))
    except (CarryError, OSError, ValueError, TypeError) as error:
        print("Geyser carry-forward refused: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
