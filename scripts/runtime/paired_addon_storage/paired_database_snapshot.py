"""Capture the disposable paired fixture DB after a server process has exited.

Only copied databases are opened by SQLite. Capture success is diagnostic evidence,
not storage acceptance, and does not replace the runner's existing phase checks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

DB_RELATIVE = Path("data-storage/Slimefun/block-storage.db")
SIDECARS = ("", "-wal", "-shm", "-journal")
TABLES = (
    "block_record", "block_data", "block_inventory", "chunk_data",
    "universal_record", "universal_data", "universal_inventory", "table_metadata",
)
MAX_TOTAL_BYTES = 64 * 1024 * 1024


def _sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _file_state(directory: Path) -> dict:
    result = {}
    for suffix in SIDECARS:
        path = directory / ("block-storage.db" + suffix)
        if path.is_symlink():
            raise RuntimeError("Fixture database inputs must not be symlinks")
        if not path.exists():
            continue
        if not path.is_file():
            raise RuntimeError("Fixture database input is not a regular file")
        result[path.name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    if "block-storage.db" not in result:
        raise RuntimeError("The exact fixture block-storage.db is missing")
    if sum(value["bytes"] for value in result.values()) > MAX_TOTAL_BYTES:
        raise RuntimeError("Database snapshot exceeds the bounded fixture size")
    return result


def _read_tables(database: Path) -> dict:
    # Deliberately omit immutable=1: SQLite must include copied WAL transactions.
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5.0)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.row_factory = sqlite3.Row
        counts = {
            table: connection.execute('SELECT count(*) FROM "' + table + '"').fetchone()[0]
            for table in TABLES
        }
        records = [
            dict(row) for row in connection.execute(
                "SELECT loc, chunk, sf_id FROM block_record ORDER BY loc LIMIT 32"
            )
        ]
        data = [
            dict(row) for row in connection.execute(
                "SELECT loc, data_key, data_val FROM block_data ORDER BY loc, data_key LIMIT 64"
            )
        ]
        inventories = []
        for row in connection.execute(
            "SELECT loc, i_slot, i_item FROM block_inventory ORDER BY loc, i_slot LIMIT 32"
        ):
            blob = row["i_item"]
            inventories.append({
                "loc": row["loc"], "slot": row["i_slot"], "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(), "prefix_hex": blob[:4].hex(),
            })
        universal = [
            dict(row) for row in connection.execute(
                "SELECT universal_uuid, sf_id, universal_traits FROM universal_record "
                "ORDER BY universal_uuid LIMIT 32"
            )
        ]
        return {
            "table_counts": counts, "block_records": records, "block_data": data,
            "block_inventory": inventories, "universal_records": universal,
            "detail_limits": {"block_record": 32, "block_data": 64,
                              "block_inventory": 32, "universal_record": 32},
            "details_truncated": {
                "block_record": counts["block_record"] > 32,
                "block_data": counts["block_data"] > 64,
                "block_inventory": counts["block_inventory"] > 32,
                "universal_record": counts["universal_record"] > 32,
            },
        }
    finally:
        connection.close()


def snapshot_database(work: Path, phase: str, pid: int, returncode: int) -> dict:
    """Call after process.wait completes and before reading/accepting its result."""
    if phase not in ("seed", "verify") or type(pid) is not int or pid <= 0:
        raise SystemExit("Invalid paired database snapshot phase/process")
    if type(returncode) is not int:
        raise SystemExit("Database snapshots require an exited child process")
    work = work.resolve(strict=True)
    database = work / DB_RELATIVE
    if database.resolve(strict=True) != database:
        raise SystemExit("Database snapshot must remain inside the exact fixture path")
    phase_file = work / "plugins/paired-ie2-phase.txt"
    if not phase_file.is_file() or phase_file.read_text(encoding="utf-8").strip() != phase:
        raise SystemExit("Database snapshot does not match the active fixture phase")
    if not (work / "plugins/PairedIE2StorageProbe.jar").is_file():
        raise SystemExit("Database snapshot requires the separate paired fixture plugin")
    inputs = work / "inputs.json"
    if not inputs.is_file():
        raise SystemExit("Database snapshot requires the paired input identity receipt")

    source_before = _file_state(database.parent)
    parent = work / "phase-database-snapshots"
    if parent.is_symlink():
        raise SystemExit("Database snapshot destination must not be a symlink")
    snapshot = parent / phase
    snapshot.mkdir(parents=True, exist_ok=False)
    raw = snapshot / "raw"
    raw.mkdir()
    receipt = {
        "schema": 1, "phase": phase, "pid": pid, "child_returncode": returncode,
        "capture_boundary": "After child process wait/exit and before phase result acceptance",
        "scope": "Exact disposable fixture block-storage.db and its WAL/SHM/journal only",
        "helper_sha256": _sha256(Path(__file__).resolve()),
        "inputs_receipt_sha256": _sha256(inputs),
        "original_database": str(database), "source_before": source_before,
        "raw_directory": str(raw), "original_database_opened_by_sqlite": False,
        "sqlite_uri_mode": "ro", "sqlite_immutable": False,
        "copy_scope": "Preserved raw copies plus a separate temporary SQLite inspection copy",
        "storage_acceptance": "Unchanged runner phase checks remain authoritative",
    }
    problem = None
    try:
        for name in source_before:
            with (database.parent / name).open("rb") as source, (raw / name).open("xb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
        receipt["raw_before"] = _file_state(raw)
        if receipt["raw_before"] != source_before:
            raise RuntimeError("Raw database snapshot bytes differ from source")
        if _file_state(database.parent) != source_before:
            raise RuntimeError("Source database changed while its raw snapshot was copied")

        with tempfile.TemporaryDirectory(prefix="sqlite-inspection-", dir=snapshot) as temporary:
            inspection = Path(temporary)
            for name in source_before:
                shutil.copyfile(raw / name, inspection / name)
            receipt["inspection_before"] = _file_state(inspection)
            if receipt["inspection_before"] != source_before:
                raise RuntimeError("SQLite inspection copy differs from preserved raw bytes")
            try:
                receipt["database"] = _read_tables(inspection / "block-storage.db")
            finally:
                # SQLite may legitimately update/create only this temporary SHM copy.
                receipt["inspection_after"] = _file_state(inspection)
    except Exception as error:
        problem = type(error).__name__ + ": " + str(error)

    try:
        receipt["source_after"] = _file_state(database.parent)
        receipt["raw_after"] = _file_state(raw)
        receipt["source_unchanged"] = receipt["source_after"] == source_before
        receipt["raw_copies_unchanged"] = receipt["raw_after"] == source_before
        if not receipt["source_unchanged"] or not receipt["raw_copies_unchanged"]:
            raise RuntimeError("Original database or preserved raw snapshot changed")
    except Exception as error:
        problem = (problem + "; " if problem else "") + type(error).__name__ + ": " + str(error)

    receipt["status"] = (
        "FAIL_READONLY_POST_PROCESS_DATABASE_SNAPSHOT" if problem
        else "PASS_READONLY_POST_PROCESS_DATABASE_SNAPSHOT"
    )
    if problem:
        receipt["error"] = problem
    report = snapshot / "snapshot.json"
    report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if problem:
        raise SystemExit("Read-only database snapshot failed; inspect " + str(report))
    return receipt

