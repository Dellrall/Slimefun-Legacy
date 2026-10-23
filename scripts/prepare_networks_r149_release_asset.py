#!/usr/bin/env python3
"""Prepare an exact-source Networks-only v4.1.76 addon ZIP update.

No GitHub mutations; the calling workflow alone owns guarded publication.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile

BUNDLE_NAME = "SF_Addons_1.21.11-26.3.zip"
NET_REPO = "wickidcow/SF_NetworksExp"
NET_OLD_NAME = "SF_Networks1.0.60.jar"
NET_OLD_SOURCE = "d41d362c8b71073dca41abc24f6ef6a5a8688fff"
NET_NEW_NAME = "SF_Networks1.0.61.jar"
NET_NEW_SOURCE = "9bf9f48b49dbedbf9e617ca840d9ccd57cf0c717"
HUD_REPO = "wickidcow/SF_SlimeHUD"
HUD_SOURCE = "72ba3ca673beb2b48c15b5dc77bf1d1880f8a1e3"
MAGIC_REPO = "wickidcow/SF_MagicExpansion"
MAGIC_SOURCE = "e0097f1d8e984e8d19692fcc5a28729366b72d48"
IE2_REPO = "wickidcow/SF_InfinityExpansion2"
CORE_SOURCE = "9075ea852095b28543aaa1456bc2576778cb4c4d"


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def extract(blob: bytes) -> tuple[dict[str, bytes], dict]:
    with ZipFile(io.BytesIO(blob)) as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        require(len(names) == len(set(names)), "Duplicate ZIP entries")
        require(all(name and not name.startswith("/") and "\\" not in name
                    and ".." not in name.split("/") for name in names),
                "Invalid ZIP entry path")
        require(archive.testzip() is None, "ZIP CRC failed")
        require(all((m.external_attr >> 16) & 0o170000 != 0o120000 for m in members),
                "Symlink entry is forbidden")
        return {m.filename: archive.read(m) for m in members}, {m.filename: copy.copy(m) for m in members}


def update(base: bytes, new_networks: bytes, source_matrix: dict, old_digest: str, new_digest: str):
    require(digest(base) == old_digest, "Public r148 ZIP SHA-256 changed; refuse overwrite")
    require(digest(new_networks) == new_digest, "Networks 1.0.61 release JAR SHA-256 mismatch")
    plugin, _ = extract(new_networks)
    require("plugin.yml" in plugin, "Missing Networks plugin descriptor")
    descriptor = plugin["plugin.yml"].decode("utf-8")
    require(re.search(r"(?m)^name:\s*Networks\s*$", descriptor) is not None,
            "Networks plugin name changed")
    require(re.search(r"(?m)^version:\s*1\.0\.61\s*$", descriptor) is not None,
            "Networks plugin version incorrect")

    old_files, infos = extract(base)
    require("SF_ADDON_MANIFEST.json" in old_files and "SHA256SUMS.txt" in old_files,
            "Published bundle is missing metadata")
    old_manifest = json.loads(old_files["SF_ADDON_MANIFEST.json"])
    require(old_manifest.get("bundle") == BUNDLE_NAME, "Wrong bundle identity")
    require(old_manifest.get("bundle_revision") == 148, "Expected published r148 baseline")
    require(old_manifest.get("core_source_commit") == CORE_SOURCE, "Unexpected core source identity")
    old_rows = old_manifest.get("addons")
    require(isinstance(old_rows, list) and len(old_rows) == 45, "Expected 45 addon records")
    require(len({x["repository"] for x in old_rows}) == 45, "Duplicate addon repository")
    require(len({x["jar"] for x in old_rows}) == 45, "Duplicate addon JAR")
    require({x["jar"] for x in old_rows} == {x for x in old_files if x.endswith(".jar")},
            "Published archive JAR set differs from manifest")
    for row in old_rows:
        require(digest(old_files[row["jar"]]) == row["sha256"],
                "Published addon SHA-256 mismatch: " + row["jar"])
    checksums = sorted(old_files["SHA256SUMS.txt"].decode("utf-8").strip().splitlines())
    require(checksums == sorted(f'{digest(old_files[row["jar"]])}  {row["jar"]}' for row in old_rows),
            "Published SHA256SUMS.txt differs from actual content")
    old_by_repo = {x["repository"]: x for x in old_rows}
    require(old_by_repo[NET_REPO]["jar"] == NET_OLD_NAME
            and old_by_repo[NET_REPO]["commit"] == NET_OLD_SOURCE,
            "Published Networks 1.0.60 source identity changed")
    require(old_by_repo[HUD_REPO]["jar"] == "SF_SlimeHUD2.0.7.jar"
            and old_by_repo[HUD_REPO]["commit"] == HUD_SOURCE,
            "Published SlimeHUD 2.0.7 source is not retained")
    require(old_by_repo[MAGIC_REPO]["jar"] == "SF_MagicExpansion1.1.17.jar"
            and old_by_repo[MAGIC_REPO]["commit"] == MAGIC_SOURCE,
            "Published MagicExpansion 1.1.17 source is not retained")
    require(old_by_repo[IE2_REPO]["jar"] == "SF_InfinityExpansion2.0.15.jar",
            "InfinityExpansion2 2.0.15 was not retained")

    require(type(source_matrix.get("bundle_revision")) is int
            and source_matrix["bundle_revision"] == 149, "Source matrix must pin r149")
    source_rows = source_matrix.get("addons")
    require(isinstance(source_rows, list) and len(source_rows) == 45,
            "Expected 45 source-selected addons")
    source_by_repo = {x["repository"]: x for x in source_rows}
    require(set(source_by_repo) == set(old_by_repo), "Source matrix changed maintained addons")
    require(source_by_repo[NET_REPO]["source_commit"] == NET_NEW_SOURCE,
            "Networks 1.0.61 source commit not selected")
    require(source_by_repo[HUD_REPO]["source_commit"] == HUD_SOURCE,
            "SlimeHUD 2.0.7 source changed")
    require(source_by_repo[MAGIC_REPO]["source_commit"] == MAGIC_SOURCE,
            "MagicExpansion source changed")
    for repo, old in old_by_repo.items():
        if repo != NET_REPO:
            require(source_by_repo[repo]["source_commit"] == old["commit"],
                    "Unexpected extra addon source change: " + repo)

    new_manifest = copy.deepcopy(old_manifest)
    new_manifest["bundle_revision"] = 149
    new_row = copy.deepcopy(old_by_repo[NET_REPO])
    new_row.update({"jar": NET_NEW_NAME, "source_jar": NET_NEW_NAME,
                    "version": "1.0.61", "commit": NET_NEW_SOURCE, "sha256": new_digest})
    new_manifest["addons"] = [new_row if row["repository"] == NET_REPO else row for row in old_rows]
    new_files = dict(old_files)
    del new_files[NET_OLD_NAME]
    new_files[NET_NEW_NAME] = new_networks
    new_files["SF_ADDON_MANIFEST.json"] = (
        json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n").encode()
    new_files["SHA256SUMS.txt"] = ("\n".join(sorted(
        f'{digest(new_files[row["jar"]])}  {row["jar"]}' for row in new_manifest["addons"]
    )) + "\n").encode()
    require({x for x in new_files if x.endswith(".jar")}
            == {r["jar"] for r in new_manifest["addons"]}, "New addon filenames mismatch")
    require(all(new_files[name] == old_files[name] for name in old_files
                if name not in {NET_OLD_NAME, "SF_ADDON_MANIFEST.json", "SHA256SUMS.txt"}),
            "Unrelated ZIP entry changed")

    out = io.BytesIO()
    with ZipFile(out, "w", allowZip64=True) as z:
        for name in old_files:
            info = infos[name]
            if name == NET_OLD_NAME:
                info.filename = NET_NEW_NAME
                z.writestr(info, new_networks)
            else:
                z.writestr(info, new_files[name])
    rebuilt = out.getvalue()
    actual, _ = extract(rebuilt)
    require(actual == new_files, "ZIP serialization changed member bytes")
    require(len([x for x in actual if x.endswith('.jar')]) == 45, "Wrong addon count")
    return rebuilt, {"bundle_revision": 149, "addon_count": 45,
                     "other_addon_jars_unchanged": 44,
                     "old_bundle_sha256": old_digest, "new_bundle_sha256": digest(rebuilt),
                     "new_networks_jar_sha256": new_digest,
                     "source_commit": NET_NEW_SOURCE,
                     "slimehud_2_0_7_preserved_sha256": digest(old_files[old_by_repo[HUD_REPO]["jar"]]),
                     "magic_1_1_17_preserved_sha256": digest(old_files[old_by_repo[MAGIC_REPO]["jar"]]),
                     "ie2_2_0_15_preserved_sha256": digest(old_files[old_by_repo[IE2_REPO]["jar"]])}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--old", type=Path, required=True)
    p.add_argument("--networks", type=Path, required=True)
    p.add_argument("--matrix", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--old-sha256", required=True)
    p.add_argument("--networks-sha256", required=True)
    args = p.parse_args()
    archive, receipt = update(args.old.read_bytes(), args.networks.read_bytes(),
                              json.loads(args.matrix.read_text(encoding="utf-8")),
                              args.old_sha256, args.networks_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(archive)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
