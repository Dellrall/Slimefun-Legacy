#!/usr/bin/env python3
"""Read-only release-asset preflight and preservation checks.

Consumes GitHub REST release JSON. This program never calls GitHub or deletes
files/assets. The workflow executes only its explicit legacy-asset deletion plan.
The API digest is upload metadata, not a fresh download/hash of release bytes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BUNDLE = "SF_Addons_1.21.11-26.3.zip"
PACK = "SlimefunLegacyRP.zip"
BEDROCK_PACK = "GEYSER_SFL_RP_Experimental_v0.0.1.zip"
BEDROCK_PIN_PATH = Path(__file__).resolve().parents[1] / "compatibility/bedrock-resource-pack-release.json"
ROLLBACK = "SF_Addons_r136_1.21.11-26.3.zip"
# The existing, deliberately retained asset; not permission for arbitrary extras.
# Source: release 412654205 / asset 641318435, inspected October 15, 2026.
ROLLBACK_PIN = {
    "release_id": 412654205,
    "tag": "v4.1.74",
    "id": 641318435,
    "name": ROLLBACK,
    "size": 24440999,
    "digest": "sha256:79b9cb70a522a9ed97de3d9107d4750a913c4372043e5ee8cfeca0a1f85afc9f",
}
LEGACY_EXACT = {
    "SFL_AddonsNDependencies.zip",
    "SFL_AddonsNDependencies.sha256",
    "SFL_Addons_1.21.11-26.3.zip",
}


class PolicyError(ValueError):
    """Refuse ambiguous, incomplete or unapproved release state."""


def is_legacy(name: str) -> bool:
    return (
        name in LEGACY_EXACT
        or re.fullmatch(r"SF_.*\.jar", name) is not None
        or re.fullmatch(r"SlimefunLegacy-ResourcePack-.*\.zip", name) is not None
    )


def positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def retained_identity(asset: dict[str, Any]) -> dict[str, Any]:
    digest = asset.get("digest")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise PolicyError(f"Missing/invalid SHA-256 metadata for retained asset {asset['name']}")
    if not positive_int(asset.get("size")):
        raise PolicyError(f"Empty/invalid retained asset {asset['name']}")
    return {key: asset[key] for key in ("id", "name", "size", "digest", "state")}


def load_bedrock_pin() -> dict[str, Any]:
    pin = load_json(BEDROCK_PIN_PATH)
    if not isinstance(pin, dict) or type(pin.get("schema_version")) is not int or pin["schema_version"] != 1:
        raise PolicyError("Invalid Bedrock preservation pin schema")
    if pin.get("repository") != "wickidcow/Slimefun-Legacy" or pin.get("asset_name") != BEDROCK_PACK:
        raise PolicyError("Unexpected Bedrock preservation repository or filename")
    for key in ("release_id", "asset_id", "size_bytes"):
        if not positive_int(pin.get(key)):
            raise PolicyError(f"Invalid Bedrock preservation pin {key}")
    if not isinstance(pin.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]):
        raise PolicyError("Invalid Bedrock preservation SHA-256 pin")
    tags = pin.get("carry_forward_tags")
    if (not isinstance(tags, list) or not tags
            or any(not isinstance(tag, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag)
                   for tag in tags)
            or len(set(tags)) != len(tags)):
        raise PolicyError("Bedrock carry-forward tags must be an explicit unique stable-tag list")
    origin = pin.get("release_tag")
    if not isinstance(origin, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", origin) or origin in tags:
        raise PolicyError("Invalid Bedrock preservation origin tag")
    return pin


def retained_bedrock_identity(release: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    pin = load_bedrock_pin()
    tag = release["tag_name"]
    if tag == pin["release_tag"]:
        if release["id"] != pin["release_id"] or asset["id"] != pin["asset_id"]:
            raise PolicyError("Original Bedrock release/asset identity differs from the reviewed pin")
    elif tag not in pin["carry_forward_tags"]:
        raise PolicyError("Bedrock pack is not approved on this release tag")
    identity = retained_identity(asset)
    if identity["size"] != pin["size_bytes"] or identity["digest"] != "sha256:" + pin["sha256"]:
        raise PolicyError("Bedrock pack size/digest differs from the reviewed carry-forward pin")
    return identity


def plan_release(release: Any, *, allow_legacy: bool = True) -> dict[str, Any]:
    if not isinstance(release, dict) or not positive_int(release.get("id")):
        raise PolicyError("Expected a GitHub release object with a positive numeric ID")
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise PolicyError("Cleanup requires an explicitly non-draft, non-prerelease release")
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise PolicyError("Expected a stable vMAJOR.MINOR.PATCH release tag")
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise PolicyError("Missing or invalid assets array")
    core = f"Slimefun-Legacy{tag[1:]}.jar"
    names: set[str] = set()
    ids: set[int] = set()
    keep: dict[str, dict[str, Any]] = {}
    remove: list[dict[str, Any]] = []
    for asset in assets:
        if not isinstance(asset, dict) or not positive_int(asset.get("id")):
            raise PolicyError("Asset identity must be a positive numeric ID")
        name = asset.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_().+\-]+", name):
            raise PolicyError("Asset names must be unambiguous, flat filenames")
        if name in names or asset["id"] in ids:
            raise PolicyError("Duplicate asset name or numeric ID")
        names.add(name)
        ids.add(asset["id"])
        if asset.get("state") != "uploaded":
            raise PolicyError(f"Asset is not fully uploaded: {name}")
        if name in {core, BUNDLE, PACK}:
            keep[name] = retained_identity(asset)
        elif name == BEDROCK_PACK:
            keep[name] = retained_bedrock_identity(release, asset)
        elif name == ROLLBACK:
            expected = ROLLBACK_PIN
            if release["id"] != expected["release_id"] or tag != expected["tag"]:
                raise PolicyError("The retained r136 rollback belongs only to its reviewed release")
            identity = retained_identity(asset)
            if any(identity[key] != expected[key] for key in ("id", "name", "size", "digest")):
                raise PolicyError("Retained r136 rollback identity/digest differs from the reviewed pin")
            keep[name] = identity
        elif allow_legacy and is_legacy(name):
            remove.append({"id": asset["id"], "name": name})
        else:
            raise PolicyError(f"Unapproved release asset: {name}; no cleanup is authorized")
    if core not in keep or BUNDLE not in keep:
        raise PolicyError("Expected the exact tag-matching core JAR and canonical addon bundle")
    if remove and release.get("immutable") is True:
        raise PolicyError("Cannot remove assets from an immutable release")
    return {
        "release_id": release["id"],
        "tag": tag,
        "retained": dict(sorted(keep.items())),
        "remove": sorted(remove, key=lambda asset: asset["id"]),
    }


def verify_preserved(before: Any, after: Any) -> dict[str, Any]:
    planned = plan_release(before)
    actual = plan_release(after, allow_legacy=False)
    if (actual["release_id"], actual["tag"]) != (planned["release_id"], planned["tag"]):
        raise PolicyError("Release identity changed during cleanup")
    if actual["retained"] != planned["retained"]:
        raise PolicyError("Retained assets changed during cleanup; preserve all original evidence")
    return actual


def load_json(path: Path) -> Any:
    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise PolicyError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "verify"))
    parser.add_argument("before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--delete-ids", type=Path)
    args = parser.parse_args(argv)
    if args.mode == "verify" and (args.after is None or args.delete_ids is not None):
        parser.error("verify requires --after and does not accept --delete-ids")
    if args.mode == "plan" and args.after is not None:
        parser.error("plan does not accept --after")
    try:
        before = load_json(args.before)
        result = (plan_release(before) if args.mode == "plan"
                  else verify_preserved(before, load_json(args.after)))
        if args.delete_ids is not None:
            # Write only after the entire preflight succeeds; the shell stops on failure.
            args.delete_ids.write_text("".join(f"{asset['id']}\n" for asset in result["remove"]), encoding="utf-8")
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"Release asset verification failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
