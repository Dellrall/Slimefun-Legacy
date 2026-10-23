#!/usr/bin/env python3
"""Rebuild the 45-addon r150 ZIP by replacing only MagicExpansion in a verified r149 archive.

This module performs no GitHub mutation: publication is guarded in its separate workflow.
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

NAME = "SF_Addons_1.21.11-26.3.zip"
MAGIC = "wickidcow/SF_MagicExpansion"
OLD_MAGIC = "SF_MagicExpansion1.1.17.jar"
NEW_MAGIC = "SF_MagicExpansion1.1.18.jar"
OLD_SOURCE = "e0097f1d8e984e8d19692fcc5a28729366b72d48"
NEW_SOURCE = "7c2c1a927176ebd0aaab4481dcc21a51320f7f10"
NETWORKS = "wickidcow/SF_NetworksExp"
NETWORKS_SOURCE = "9bf9f48b49dbedbf9e617ca840d9ccd57cf0c717"
HUD = "wickidcow/SF_SlimeHUD"
HUD_SOURCE = "72ba3ca673beb2b48c15b5dc77bf1d1880f8a1e3"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_zip(raw: bytes):
    with ZipFile(io.BytesIO(raw)) as z:
        members = z.infolist()
        names = [m.filename for m in members]
        require(len(names) == len(set(names)), "Duplicate ZIP entries")
        require(all(n and not n.startswith("/") and "\\" not in n
                    and ".." not in n.split("/") for n in names), "Unsafe ZIP paths")
        require(all((m.external_attr >> 16) & 0o170000 != 0o120000
                    for m in members), "ZIP symlink entry refused")
        require(z.testzip() is None, "ZIP member CRC failure")
        return {m.filename: z.read(m) for m in members}, {
            m.filename: copy.copy(m) for m in members}


def rebuild(base: bytes, magic: bytes, matrix: dict, old_hash: str, magic_hash: str):
    require(re.fullmatch(r"[a-f0-9]{64}", old_hash) is not None, "Old digest must be SHA-256")
    require(re.fullmatch(r"[a-f0-9]{64}", magic_hash) is not None, "JAR digest must be SHA-256")
    require(sha(base) == old_hash, "Published base ZIP changed before preparation")
    require(sha(magic) == magic_hash, "MagicExpansion JAR checksum mismatch")

    plugin, _ = read_zip(magic)
    require("plugin.yml" in plugin, "MagicExpansion plugin.yml missing")
    descriptor = plugin["plugin.yml"].decode("utf-8")
    require(re.search(r"(?m)^name:\s*magicexpansion\s*$", descriptor) is not None,
            "MagicExpansion plugin identity changed")
    require(re.search(r"(?m)^version:\s*['\"]?1\.1\.18['\"]?\s*$", descriptor) is not None,
            "MagicExpansion version must be 1.1.18")
    require(any(n.endswith("ResourceMachine.class") for n in plugin),
            "Missing resource-generator classes")

    content, infos = read_zip(base)
    require("SF_ADDON_MANIFEST.json" in content and "SHA256SUMS.txt" in content,
            "Published base missing canonical manifest or checksums")
    manifest = json.loads(content["SF_ADDON_MANIFEST.json"])
    require(manifest.get("bundle") == NAME and type(manifest.get("bundle_revision")) is int
            and manifest["bundle_revision"] == 149, "Expected canonical r149 base")
    rows = manifest.get("addons")
    require(isinstance(rows, list) and len(rows) == 45, "Expected 45 addon manifest rows")
    old = {row["repository"]: row for row in rows}
    require(len(old) == 45 and len({r["jar"] for r in rows}) == 45,
            "Duplicate addon identity")
    require({r["jar"] for r in rows} == {x for x in content if x.endswith(".jar")},
            "JAR collection differs from canonical manifest")
    for row in rows:
        require(sha(content[row["jar"]]) == row["sha256"],
                "Published addon checksum mismatch: " + row["jar"])
    expected_sums = sorted(f'{sha(content[r["jar"]])}  {r["jar"]}' for r in rows)
    require(sorted(content["SHA256SUMS.txt"].decode().splitlines()) == expected_sums,
            "Published SHA256SUMS mismatch")

    require(old[MAGIC]["jar"] == OLD_MAGIC and old[MAGIC]["commit"] == OLD_SOURCE
            and old[MAGIC]["version"] == "1.1.17", "Wrong r149 MagicExpansion identity")
    require(old[NETWORKS]["jar"] == "SF_Networks1.0.61.jar"
            and old[NETWORKS]["commit"] == NETWORKS_SOURCE, "Networks 1.0.61 missing")
    require(old[HUD]["jar"] == "SF_SlimeHUD2.0.7.jar"
            and old[HUD]["commit"] == HUD_SOURCE, "SlimeHUD 2.0.7 missing")
    require(old["wickidcow/SF_InfinityExpansion2"]["version"] == "2.0.15",
            "InfinityExpansion2 2.0.15 not retained")

    require(type(matrix.get("bundle_revision")) is int
            and matrix["bundle_revision"] == 150, "Expected exact r150 source matrix")
    selected = matrix.get("addons")
    require(isinstance(selected, list) and len(selected) == 45,
            "Expected 45 source pin records")
    pins = {row["repository"]: row["source_commit"] for row in selected}
    require(len(pins) == 45 and set(pins) == set(old), "Maintained addon roster changed")
    require(pins[MAGIC] == NEW_SOURCE, "MagicExpansion 1.1.18 source pin mismatch")
    for repo, row in old.items():
        if repo != MAGIC:
            require(pins[repo] == row["commit"], "Unrelated source pin changed: " + repo)

    new_manifest = copy.deepcopy(manifest)
    new_manifest["bundle_revision"] = 150
    new_rows = []
    for row in rows:
        row = copy.deepcopy(row)
        if row["repository"] == MAGIC:
            row.update({"jar": NEW_MAGIC, "source_jar": NEW_MAGIC,
                        "version": "1.1.18", "commit": NEW_SOURCE, "sha256": magic_hash})
        new_rows.append(row)
    new_manifest["addons"] = new_rows
    changed = dict(content)
    del changed[OLD_MAGIC]
    changed[NEW_MAGIC] = magic
    changed["SF_ADDON_MANIFEST.json"] = (
        json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n").encode()
    changed["SHA256SUMS.txt"] = ("\n".join(sorted(
        f'{sha(changed[r["jar"]])}  {r["jar"]}' for r in new_rows)) + "\n").encode()

    require({n for n in changed if n.endswith(".jar")} == {r["jar"] for r in new_rows},
            "Updated 45-JAR set mismatch")
    require(all(changed[n] == content[n] for n in content
                if n not in {OLD_MAGIC, "SF_ADDON_MANIFEST.json", "SHA256SUMS.txt"}),
            "Unrelated entry bytes changed")
    output = io.BytesIO()
    with ZipFile(output, "w", allowZip64=True) as z:
        for name, original_info in infos.items():
            info = copy.copy(original_info)
            if name == OLD_MAGIC:
                info.filename = NEW_MAGIC
                z.writestr(info, magic)
            else:
                z.writestr(info, changed[name])
    new_archive = output.getvalue()
    roundtrip, _ = read_zip(new_archive)
    require(roundtrip == changed, "ZIP serialization changed member bytes")
    require(len([n for n in roundtrip if n.endswith(".jar")]) == 45,
            "Expected 45 total addon JARs")
    return new_archive, {
        "bundle_revision": 150,
        "addon_count": 45,
        "other_addon_jars_byte_identical": 44,
        "old_bundle_sha256": old_hash,
        "new_bundle_sha256": sha(new_archive),
        "new_magic_jar_sha256": magic_hash,
        "old_magic_jar_sha256": old[MAGIC]["sha256"],
        "magic_source_commit": NEW_SOURCE,
        "network_jar_sha256_retained": old[NETWORKS]["sha256"],
        "slimehud_jar_sha256_retained": old[HUD]["sha256"],
        "core_source_commit_preserved": manifest.get("core_source_commit")
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--magic", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--old-sha256", required=True)
    parser.add_argument("--magic-sha256", required=True)
    args = parser.parse_args()
    raw, receipt = rebuild(
        args.old.read_bytes(), args.magic.read_bytes(),
        json.loads(args.matrix.read_text(encoding="utf-8")),
        args.old_sha256, args.magic_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
