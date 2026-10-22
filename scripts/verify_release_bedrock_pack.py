#!/usr/bin/env python3
"""Read-only identity and archive checks for the complete optional Geyser Bedrock pack.

This verifies the reviewed bytes and drop-in structure. It does not certify
Bedrock client rendering, texture coverage, or compatibility with other packs.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any

ASSET_NAME = "SFL_GEYSER_RP_experimental_v1.0.3_complete.zip"
ARCHIVE_PATH = "compatibility/bedrock/" + ASSET_NAME
SOURCE_ASSETS = (
    {"release_tag": "v4.1.75", "release_id": 415923695, "asset_id": 664289959,
     "asset_name": "GEYSER_SFL_RP_v0.0.2.zip", "size_bytes": 1329705,
     "sha256": "b27941425a646ba97c4789ecf2841e20f08663e79b3d538b552516d40cc67ee1"},
    {"release_tag": "v4.1.75", "release_id": 415923695, "asset_id": 664360404,
     "asset_name": "SFL_GEYSER_RP_experimental_v1.0.3.zip", "size_bytes": 1265679,
     "sha256": "90d78fcf8382bdee1bce3a364515769cb8325c174b58c34b512039502cc50e51"},
)
MAPPINGS = "custom_mappings/"
MCPACK = "packs/SlimefunBedrockRP_1.0.1.mcpack"
VALHALLA_PACK = "packs/Albion_ValhallaMMO_Bedrock_1.0.1.mcpack"
STAT_ICONS_PACK = "optional/Albion_ValhallaMMO_Stat_Icons_1.0.0.mcpack"
MCPACKS = (MCPACK, VALHALLA_PACK, STAT_ICONS_PACK)
BASE_MAPPING_NAMES = (
    "SF-Androids.json", "SF-Armors.json", "SF-Basic_Machines.json", "SF-Cargo.json",
    "SF-EG-Drinks.json", "SF-EG-Food.json", "SF-Energy&Electricity.json", "SF-Food.json",
    "SF-Gps.json", "SF-Gui.json", "SF-Items.json", "SF-Magical_Gadgets.json",
    "SF-Magical_Items.json", "SF-Resources.json", "SF-Talisman-I.json", "SF-Talisman-II.json",
    "SF-Technical_Components.json", "SF-Tools.json", "SF-Weapons.json", "SlimefunItems.json",
)
VALHALLA_MAPPING = MAPPINGS + "albion_valhallammo_mappings.json"
SKULL_MAPPING = MAPPINGS + "migrated-custom-skulls.json"
NEW_SKULL_MAPPING = MAPPINGS + "albion_slimefun_legacy_skulls.json"
SKULL_MAPPINGS = (SKULL_MAPPING, NEW_SKULL_MAPPING)
MAPPING_FILES = {MAPPINGS + name for name in BASE_MAPPING_NAMES} | {VALHALLA_MAPPING, *SKULL_MAPPINGS}
MAPPING_COUNT = 23
DOCUMENT_FILES = {"README.txt", "INSTALL.md"}


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
    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON number: {value}")
    return json.loads(data, object_pairs_hook=unique_keys, parse_constant=reject_constant)


def positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def load_pin(path: Path) -> dict[str, Any]:
    pin = json_data(path.read_bytes())
    require(isinstance(pin, dict), "Expected a Bedrock asset pin object")
    require(type(pin.get("schema_version")) is int and pin["schema_version"] == 2,
            "Unexpected Bedrock asset pin schema")
    require(pin.get("repository") == "wickidcow/Slimefun-Legacy", "Unexpected Bedrock source repository")
    require(pin.get("asset_name") == ASSET_NAME, "Unexpected Bedrock asset name")
    require(pin.get("archive_path") == ARCHIVE_PATH, "Unexpected Bedrock repository archive path")
    require(not {"release_tag", "release_id", "asset_id"} & set(pin),
            "Complete Bedrock pin must use source_assets for provenance")
    require(positive_int(pin.get("size_bytes")), "Bedrock pin size_bytes must be a positive integer")
    require(isinstance(pin.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]) is not None,
            "Invalid Bedrock asset SHA-256")
    require(pin.get("carry_forward_tags") == ["v4.1.76"],
            "Bedrock carry-forward tags must contain only the reviewed v4.1.76 successor")
    require(pin.get("stability") == "experimental", "Bedrock pack must retain its experimental qualification")
    sources = pin.get("source_assets")
    require(isinstance(sources, list) and len(sources) == len(SOURCE_ASSETS),
            "Complete Bedrock pin requires exactly two reviewed source assets")
    for source, expected in zip(sources, SOURCE_ASSETS):
        require(isinstance(source, dict) and set(source) == set(expected)
                and all(positive_int(source.get(key)) for key in ("release_id", "asset_id", "size_bytes"))
                and source == expected, "Bedrock source asset provenance mismatch")
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
    # Optional audit of the live overlay source; the historical base is not fetched.
    source = pin["source_assets"][1]
    release, asset = release_asset(path, source["release_tag"], source)
    require(release["id"] == source["release_id"], "Bedrock source release ID mismatch")
    require(asset["id"] == source["asset_id"], "Bedrock source asset ID mismatch")


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


def finite_number(value: Any) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


def identifier(value: Any, pattern: str) -> bool:
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def verify_valhalla_mapping(mapping: Any) -> None:
    require(isinstance(mapping, dict) and set(mapping) == {"format_version", "items"}
            and type(mapping["format_version"]) is int and mapping["format_version"] == 2
            and isinstance(mapping["items"], dict) and bool(mapping["items"]),
            "Invalid Valhalla format-2 mapping document")
    identifiers: set[str] = set()
    for java_item, entries in mapping["items"].items():
        require(identifier(java_item, r"minecraft:[a-z0-9_]+")
                and isinstance(entries, list) and bool(entries), "Invalid Valhalla Java item mappings")
        for entry in entries:
            require(isinstance(entry, dict)
                    and set(entry) == {"type", "model", "bedrock_identifier", "predicate", "bedrock_options"}
                    and entry["type"] == "definition" and entry["model"] == java_item
                    and identifier(entry["bedrock_identifier"], r"albion_valhalla:[a-z0-9_]+"),
                    "Invalid Valhalla item definition")
            name = entry["bedrock_identifier"]
            require(name not in identifiers, "Duplicate Valhalla Bedrock identifier")
            identifiers.add(name)
            predicates = entry["predicate"]
            require(isinstance(predicates, list) and 1 <= len(predicates) <= 2,
                    "Invalid Valhalla predicate list")
            types: set[str] = set()
            for predicate in predicates:
                require(isinstance(predicate, dict), "Invalid Valhalla predicate")
                kind = predicate.get("type")
                require(isinstance(kind, str) and kind not in types, "Duplicate or invalid Valhalla predicate type")
                types.add(kind)
                if kind == "range_dispatch":
                    require(set(predicate) == {"type", "property", "threshold", "scale", "index"}
                            and predicate["property"] == "custom_model_data"
                            and finite_number(predicate["threshold"]) and predicate["threshold"] > 0
                            and finite_number(predicate["scale"]) and predicate["scale"] == 1
                            and type(predicate["index"]) is int and predicate["index"] == 0,
                            "Invalid Valhalla custom-model-data predicate")
                elif kind == "match":
                    require(set(predicate) == {"type", "property", "value"}
                            and predicate["property"] == "charge_type"
                            and predicate["value"] in ("arrow", "rocket"), "Invalid Valhalla charge predicate")
                else:
                    raise ValueError("Unexpected Valhalla predicate type")
            require("range_dispatch" in types, "Valhalla mapping has no custom-model-data predicate")
            options = entry["bedrock_options"]
            require(isinstance(options, dict) and "icon" in options
                    and set(options) <= {"icon", "display_handheld", "tags"}
                    and identifier(options["icon"], r"albion_valhalla_[a-z0-9_]+"),
                    "Invalid Valhalla Bedrock options")
            if "display_handheld" in options:
                require(type(options["display_handheld"]) is bool, "Invalid Valhalla handheld flag")
            if "tags" in options:
                require(isinstance(options["tags"], list) and bool(options["tags"])
                        and all(tag in ("minecraft:is_armor", "minecraft:trimmable_armors") for tag in options["tags"])
                        and len(options["tags"]) == len(set(options["tags"])), "Invalid Valhalla armor tags")


def verify_skull_mapping(mapping: Any) -> None:
    require(isinstance(mapping, dict) and set(mapping) == {"format_version", "skulls"}
            and type(mapping["format_version"]) is int and mapping["format_version"] == 1
            and isinstance(mapping["skulls"], dict)
            and set(mapping["skulls"]) == {"username", "uuid", "profile", "skin_hash"},
            "Invalid skull mapping document")
    skulls = mapping["skulls"]
    require(all(skulls[key] == [] for key in ("username", "uuid", "profile")),
            "Unexpected named/profile skull mappings in the reviewed archive")
    hashes = skulls["skin_hash"]
    # Reviewed Mojang texture hashes include values shorter than 64 digits (57-64).
    require(isinstance(hashes, list) and bool(hashes)
            and all(identifier(value, r"[0-9a-f]{1,64}") for value in hashes)
            and len(hashes) == len(set(hashes)), "Invalid or duplicate skull skin hashes")


def verify_pack(data: bytes, name: str) -> int:
    with zipfile.ZipFile(io.BytesIO(data)) as pack:
        files = archive_files(pack)
        documents = {path: json_data(pack.read(path)) for path in sorted(files)
                     if path.endswith((".json", ".material"))}
        manifests = sorted(path for path in files if path.split("/")[-1] == "manifest.json")
        require(len(manifests) == 1, "Expected one Bedrock pack manifest")
        manifest = documents[manifests[0]]
        require(isinstance(manifest, dict) and type(manifest.get("format_version")) is int
                and manifest["format_version"] == 2 and isinstance(manifest.get("header"), dict),
                "Invalid Bedrock pack manifest")
        modules = manifest.get("modules")
        require(isinstance(modules, list)
                and any(isinstance(module, dict) and module.get("type") == "resources" for module in modules),
                "Bedrock pack has no resource module")
        if name == STAT_ICONS_PACK:
            require(files == {"manifest.json", "pack_icon.png", "font/glyph_ED.png", "font/glyph_EE.png"},
                    "Unexpected Bedrock stat-icon font layout")
        else:
            # Geyser accepts the original Slimefun pack's enclosing SFB-RP/ directory.
            require(name == MCPACK or manifests[0] == "manifest.json", "Unexpected Valhalla pack manifest path")
            pack_root = manifests[0][:-len("manifest.json")]
            require(any(path.startswith(pack_root + "textures/") and path.endswith(".png") for path in files),
                    "Bedrock pack contains no textures")
        return len(files)


def verify_zip(path: Path, pin: dict[str, Any]) -> dict[str, int]:
    data = path.read_bytes()
    require(len(data) == pin["size_bytes"], "Bedrock ZIP size mismatch")
    require(hashlib.sha256(data).hexdigest() == pin["sha256"], "Bedrock ZIP SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = archive_files(archive)
        require(files == MAPPING_FILES | set(MCPACKS) | DOCUMENT_FILES,
                "Unexpected files in the pinned Bedrock drop-in ZIP; "
                "require exactly 23 mappings, three packs and two guides")
        require(all(not entry.is_dir() or entry.filename.rstrip("/") in {
            "custom_mappings", "packs", "optional"
        } for entry in archive.infolist()), "Unexpected directories in the pinned Bedrock drop-in ZIP")
        for name in sorted(DOCUMENT_FILES):
            require(bool(archive.read(name).decode("utf-8").strip()), f"Empty Bedrock installation document: {name}")
        skull_hashes: set[str] = set()
        for name in sorted(MAPPING_FILES):
            mapping = json_data(archive.read(name))
            if name == VALHALLA_MAPPING:
                verify_valhalla_mapping(mapping)
            elif name in SKULL_MAPPINGS:
                verify_skull_mapping(mapping)
                hashes = set(mapping["skulls"]["skin_hash"])
                require(skull_hashes.isdisjoint(hashes), "Duplicate skull skin hashes across mapping files")
                skull_hashes.update(hashes)
            else:
                require(isinstance(mapping, dict) and mapping.get("format_version") == "1"
                        and isinstance(mapping.get("items"), dict) and bool(mapping["items"]),
                        f"Invalid Geyser custom mapping document: {name}")
        pack_files = sum(verify_pack(archive.read(name), name) for name in MCPACKS)
    return {"mapping_files": MAPPING_COUNT, "resource_packs": len(MCPACKS), "pack_files": pack_files}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--pin", type=Path)
    parser.add_argument("--release-json", type=Path,
                        help="Optional current overlay source metadata audit; historical assets are not required")
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
