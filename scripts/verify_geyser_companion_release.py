#!/usr/bin/env python3
"""Release-only carry-forward of an opaque, pinned Geyser companion ZIP.

No Minecraft, Geyser, or Slimefun runtime code is imported or changed here.
Only GitHub release metadata and exact byte identity are checked.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PIN_FILE = Path(__file__).resolve().parents[1] / "compatibility/geyser-companion-release.json"
CORE_PREFIX = "Slimefun-Legacy"
ADDONS = "SF_Addons_1.21.11-26.3.zip"
JAVA_PACK = "SlimefunLegacyRP.zip"


class CarryForwardError(ValueError):
    """Refuse to publish an unpinned or ambiguously sourced release download."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CarryForwardError(message)


def positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def read_json(path: Path) -> dict:
    def distinct_keys(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=distinct_keys)
    require(isinstance(data, dict), "Expected JSON object")
    return data


def load_pin(path: Path = PIN_FILE) -> dict:
    pin = read_json(path)
    require(set(pin) == {"schema_version", "repository", "source_release_tag", "source_release_id",
                         "source_asset_id", "asset_name", "size_bytes", "sha256", "mode", "note"},
            "Unexpected companion source pin fields")
    require(type(pin["schema_version"]) is int and pin["schema_version"] == 1,
            "Invalid companion pin schema")
    require(pin["repository"] == "wickidcow/Slimefun-Legacy", "Wrong source repository")
    require(pin["source_release_tag"] == "v4.1.77", "The approved source must be v4.1.77")
    require(pin["source_release_id"] == 421464301 and
            type(pin["source_release_id"]) is int, "Source release ID changed")
    require(pin["source_asset_id"] == 669444618 and
            type(pin["source_asset_id"]) is int, "Source asset ID changed")
    require(pin["asset_name"] == "SlimefunLegacyRP_Geyser.zip", "Companion filename changed")
    require(positive_int(pin["size_bytes"]) and pin["size_bytes"] == 1339867,
            "Companion byte count changed")
    require(isinstance(pin["sha256"], str) and
            pin["sha256"] == "e11e5f8e6ede75a17421039e50178e83e11e9cf7f020e99596cfc078801b8c58",
            "Companion SHA-256 changed")
    require(pin["mode"] == "opaque-release-companion", "Companion is download-only")
    require(isinstance(pin["note"], str) and bool(pin["note"]), "Missing source note")
    return pin


def stable_version(tag: object) -> tuple[int, int, int]:
    require(isinstance(tag, str), "Release tag must be a string")
    match = re.fullmatch(r"v([0-9]+)\.([0-9]+)\.([0-9]+)", tag)
    require(match is not None, "Expected a stable vMAJOR.MINOR.PATCH release tag")
    return tuple(map(int, match.groups()))


def assets(release: dict) -> dict[str, dict]:
    require(isinstance(release, dict) and positive_int(release.get("id")),
            "Missing numeric GitHub release ID")
    require(release.get("draft") is False and release.get("prerelease") is False,
            "Refusing draft or prerelease downloads")
    names = release.get("assets")
    require(isinstance(names, list), "Missing release asset list")
    out = {}
    ids = set()
    for item in names:
        require(isinstance(item, dict) and positive_int(item.get("id")),
                "Invalid asset numeric identity")
        name = item.get("name")
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.+\-]+", name) is not None,
                "Invalid asset filename")
        require(name not in out and item["id"] not in ids, "Duplicate release asset")
        require(item.get("state") == "uploaded", "Asset upload is incomplete: " + name)
        ids.add(item["id"])
        out[name] = item
    return out


def identity(item: dict) -> tuple[int, str, int, str, str]:
    return (item["id"], item["name"], item.get("size"), item.get("digest"), item.get("state"))


def check_companion(item: dict, pin: dict, *, source: bool) -> None:
    require(item.get("name") == pin["asset_name"], "Wrong companion asset name")
    if source:
        require(item.get("id") == pin["source_asset_id"], "Source asset ID mismatch")
    require(item.get("size") == pin["size_bytes"], "Companion size mismatch")
    require(item.get("digest") == "sha256:" + pin["sha256"], "Companion SHA-256 mismatch")


def plan(source: dict, target: dict, pin: dict) -> dict:
    require(source.get("tag_name") == pin["source_release_tag"] and
            source.get("id") == pin["source_release_id"], "Approved release identity changed")
    source_assets = assets(source)
    require(pin["asset_name"] in source_assets, "Approved release lost its companion ZIP")
    check_companion(source_assets[pin["asset_name"]], pin, source=True)

    target_version = stable_version(target.get("tag_name"))
    require(target_version >= stable_version(pin["source_release_tag"]),
            "Do not attach the companion to a release before v4.1.77")
    target_assets = assets(target)
    for required in (CORE_PREFIX + target["tag_name"][1:] + ".jar", ADDONS, JAVA_PACK):
        require(required in target_assets, "Missing required Java-side release asset: " + required)
    if target["tag_name"] == pin["source_release_tag"]:
        require(target["id"] == pin["source_release_id"],
                "Source tag does not refer to the approved release")
    current = target_assets.get(pin["asset_name"])
    if current is not None:
        check_companion(current, pin, source=target["tag_name"] == pin["source_release_tag"])
    return {
        "action": "verify" if current is not None else "upload",
        "target_tag": target["tag_name"],
        "target_release_id": target["id"],
        "source_tag": pin["source_release_tag"],
        "asset_name": pin["asset_name"],
        "sha256": pin["sha256"],
        "size_bytes": pin["size_bytes"],
    }


def verify_after(source: dict, before: dict, after: dict, pin: dict) -> dict:
    intended = plan(source, before, pin)
    require(before["id"] == after.get("id") and before["tag_name"] == after.get("tag_name"),
            "Target release changed during copy")
    current = plan(source, after, pin)
    require(current["action"] == "verify", "Copied companion is missing")
    before_assets, after_assets = assets(before), assets(after)
    for name, item in before_assets.items():
        require(name in after_assets and identity(item) == identity(after_assets[name]),
                "Existing release asset was changed: " + name)
    added = set(after_assets) - set(before_assets)
    require(added == ({pin["asset_name"]} if intended["action"] == "upload" else set()),
            "Unexpected assets added during copy")
    return {
        "result": "PASS",
        "action": intended["action"],
        "target_tag": intended["target_tag"],
        "sha256": pin["sha256"],
        "size_bytes": pin["size_bytes"],
        "other_assets_preserved": len(before_assets),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("plan", "verify"))
    p.add_argument("--pin", type=Path, default=PIN_FILE)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--before", required=True, type=Path)
    p.add_argument("--after", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    try:
        pin = load_pin(args.pin)
        source = read_json(args.source)
        before = read_json(args.before)
        if args.action == "verify":
            require(args.after is not None, "Verification needs --after")
            result = verify_after(source, before, read_json(args.after), pin)
        else:
            require(args.after is None, "Planning must not receive --after")
            result = plan(source, before, pin)
        payload = json.dumps(result, indent=2) + "\n"
        if args.output is not None:
            args.output.write_text(payload, encoding="utf-8")
        print(payload, end="")
    except (CarryForwardError, OSError, ValueError, KeyError, TypeError) as error:
        print("Geyser companion release verification refused: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
