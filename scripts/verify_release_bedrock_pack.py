#!/usr/bin/env python3
"""Read-only identity and archive checks for the optional Geyser Bedrock download.

This verifies the reviewed bytes and drop-in structure. It does not certify
Bedrock client rendering, texture coverage, or compatibility with other packs.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any

ASSET_NAME = "GEYSER_SFL_RP_Experimental_v0.0.1.zip"
MAPPINGS = "Geyser-Spigot/custom_mappings/"
MCPACK = "Geyser-Spigot/packs/SlimefunBedrockRP.mcpack"
MAPPING_COUNT = 20


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def json_data(data: bytes | str) -> Any:
    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique_keys)


def positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def release_tag(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", value) is not None


def load_pin(path: Path) -> dict[str, Any]:
    pin = json_data(path.read_bytes())
    require(isinstance(pin, dict), "Expected a Bedrock asset pin object")
    require(type(pin.get("schema_version")) is int and pin["schema_version"] == 1,
            "Unexpected Bedrock asset pin schema")
    require(pin.get("repository") == "wickidcow/Slimefun-Legacy", "Unexpected Bedrock source repository")
    require(release_tag(pin.get("release_tag")), "Invalid Bedrock source release tag")
    require(pin.get("asset_name") == ASSET_NAME, "Unexpected Bedrock asset name")
    for key in ("release_id", "asset_id", "size_bytes"):
        require(positive_int(pin.get(key)), f"Bedrock pin {key} must be a positive integer")
    require(isinstance(pin.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]) is not None,
            "Invalid Bedrock asset SHA-256")
    targets = pin.get("carry_forward_tags")
    require(isinstance(targets, list) and bool(targets) and all(release_tag(tag) for tag in targets),
            "Bedrock carry-forward tags must be an explicit nonempty stable-tag list")
    require(len(targets) == len(set(targets)) and pin["release_tag"] not in targets,
            "Duplicate/source tag in Bedrock carry-forward tags")
    require(pin.get("stability") == "experimental", "Bedrock pack must retain its experimental qualification")
    return pin


def release_asset(path: Path, tag: str, pin: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    release = json_data(path.read_bytes())
    require(isinstance(release, dict) and positive_int(release.get("id")), "Invalid release identity")
    require(release.get("tag_name") == tag, "Bedrock release tag mismatch")
    require(release.get("draft") is False and release.get("prerelease") is False,
            "Bedrock asset release must be published and non-prerelease")
    assets = release.get("assets")
    require(isinstance(assets, list), "Release assets must be an array")
    names: set[str] = set()
    ids: set[int] = set()
    selected = None
    for asset in assets:
        require(isinstance(asset, dict) and positive_int(asset.get("id")), "Invalid asset identity")
        name = asset.get("name")
        require(isinstance(name, str) and bool(name), "Invalid asset name")
        require(name not in names and asset["id"] not in ids, "Duplicate release asset name or ID")
        names.add(name)
        ids.add(asset["id"])
        if name == pin["asset_name"]:
            selected = asset
    require(selected is not None, f"Release is missing {pin['asset_name']}")
    require(selected.get("state") == "uploaded", "Bedrock asset is not fully uploaded")
    require(type(selected.get("size")) is int and selected["size"] == pin["size_bytes"],
            "Bedrock asset size mismatch")
    require(selected.get("digest") == "sha256:" + pin["sha256"], "Bedrock asset GitHub digest mismatch")
    return release, selected


def verify_source_release(path: Path, pin: dict[str, Any]) -> None:
    release, asset = release_asset(path, pin["release_tag"], pin)
    require(release["id"] == pin["release_id"], "Bedrock source release ID mismatch")
    require(asset["id"] == pin["asset_id"], "Bedrock source asset ID mismatch")


def verify_target_release(path: Path, tag: str, pin: dict[str, Any]) -> None:
    verify_target_tag(tag, pin)
    release_asset(path, tag, pin)


def verify_target_tag(tag: str, pin: dict[str, Any]) -> None:
    require(tag in pin["carry_forward_tags"], "Bedrock target release tag is not approved in the pin")


def archive_files(archive: zipfile.ZipFile) -> set[str]:
    names: set[str] = set()
    files: set[str] = set()
    for entry in archive.infolist():
        name = entry.filename[:-1] if entry.is_dir() else entry.filename
        parts = name.split("/")
        require(bool(name) and not name.startswith("/") and "\\" not in name
                and ":" not in parts[0] and all(part not in ("", ".", "..") for part in parts),
                f"Unsafe ZIP path: {entry.filename}")
        require(name not in names, f"Duplicate ZIP path: {name}")
        require(not stat.S_ISLNK(entry.external_attr >> 16), f"Symlink ZIP entry: {name}")
        require(not (entry.flag_bits & 1), f"Encrypted ZIP entry: {name}")
        names.add(name)
        if not entry.is_dir():
            files.add(name)
    require(archive.testzip() is None, "ZIP CRC failure")
    return files


def verify_zip(path: Path, pin: dict[str, Any]) -> dict[str, int]:
    data = path.read_bytes()
    require(len(data) == pin["size_bytes"], "Bedrock ZIP size mismatch")
    require(hashlib.sha256(data).hexdigest() == pin["sha256"], "Bedrock ZIP SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = archive_files(archive)
        mappings = sorted(name for name in files if name.startswith(MAPPINGS)
                          and "/" not in name[len(MAPPINGS):] and name.endswith(".json"))
        require(len(mappings) == MAPPING_COUNT, f"Expected {MAPPING_COUNT} Bedrock custom mapping files")
        require(MCPACK in files, "Bedrock drop-in ZIP is missing its .mcpack")
        require(files == set(mappings) | {MCPACK}, "Unexpected files in the pinned Bedrock drop-in ZIP")
        for name in mappings:
            mapping = json_data(archive.read(name))
            require(isinstance(mapping, dict) and mapping.get("format_version") == "1"
                    and isinstance(mapping.get("items"), dict) and bool(mapping["items"]),
                    f"Invalid Geyser custom mapping document: {name}")
        with zipfile.ZipFile(io.BytesIO(archive.read(MCPACK))) as pack:
            pack_files = archive_files(pack)
            # Geyser accepts the existing pack's enclosing SFB-RP/ directory.
            manifests = sorted(name for name in pack_files if name.split("/")[-1] == "manifest.json")
            require(len(manifests) == 1, "Expected one Bedrock pack manifest")
            manifest = json_data(pack.read(manifests[0]))
            require(isinstance(manifest, dict) and manifest.get("format_version") == 2
                    and isinstance(manifest.get("header"), dict), "Invalid Bedrock pack manifest")
            modules = manifest.get("modules")
            require(isinstance(modules, list)
                    and any(isinstance(module, dict) and module.get("type") == "resources" for module in modules),
                    "Bedrock pack has no resource module")
            pack_root = manifests[0][:-len("manifest.json")]
            require(any(name.startswith(pack_root + "textures/") for name in pack_files),
                    "Bedrock pack contains no textures")
    return {"mapping_files": len(mappings), "pack_files": len(pack_files)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--pin", type=Path)
    parser.add_argument("--release-json", type=Path)
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--target-release-json", type=Path)
    parser.add_argument("--target-tag")
    args = parser.parse_args(argv)
    if args.target_release_json is not None and args.target_tag is None:
        parser.error("--target-release-json requires --target-tag")
    try:
        pin = load_pin(args.pin or args.root / "compatibility/bedrock-resource-pack-release.json")
        if args.target_tag is not None:
            verify_target_tag(args.target_tag, pin)
        if args.release_json is not None:
            verify_source_release(args.release_json, pin)
        if args.zip is not None:
            verify_zip(args.zip, pin)
        if args.target_release_json is not None:
            verify_target_release(args.target_release_json, args.target_tag, pin)
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile, RuntimeError) as error:
        print(f"Bedrock pack verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Bedrock pack verification passed: {pin['asset_name']} / {pin['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
