#!/usr/bin/env python3
"""Check a compiled Slimefun JAR against the supported Bukkit/Paper API floor.

The production core is compiled against the modern Paper API. JVM member references
can therefore bind to covariant overrides or other descriptors that do not exist on
the supported 1.21.11 floor even when the same Java source also compiles there.

This checker inspects the production JAR's constant-pool references and resolves every
Bukkit/Paper class, method, and field against the resolved modern and floor platform classpaths.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from check_addon_binary_linkage import (
    ClassFormatError,
    MemberRef,
    load_classes,
    normalize_class_name,
    resolves_member,
)

DEFAULT_PREFIXES = ("org/bukkit/", "io/papermc/paper/", "com/destroystokyo/paper/")


@dataclass
class PlatformLinkageResult:
    core_jar: str
    platform_classpath: list[str]
    modern_platform_classpath: list[str]
    core_classes: int
    checked_class_references: int
    checked_member_references: int
    missing_classes: list[str]
    missing_methods: list[MemberRef]
    missing_fields: list[MemberRef]

    @property
    def passed(self) -> bool:
        return not self.missing_classes and not self.missing_methods and not self.missing_fields

    def to_json(self) -> dict[str, object]:
        def member(ref: MemberRef) -> dict[str, str]:
            return {
                "owner": ref.owner,
                "name": ref.name,
                "descriptor": ref.descriptor,
                "kind": ref.kind,
            }

        return {
            "status": "PASS" if self.passed else "FAIL",
            "core_jar": self.core_jar,
            "platform_classpath": self.platform_classpath,
            "modern_platform_classpath": self.modern_platform_classpath,
            "core_classes": self.core_classes,
            "checked_class_references": self.checked_class_references,
            "checked_member_references": self.checked_member_references,
            "missing_classes": self.missing_classes,
            "missing_methods": [member(ref) for ref in self.missing_methods],
            "missing_fields": [member(ref) for ref in self.missing_fields],
        }


def is_platform_name(name: str, prefixes: tuple[str, ...]) -> bool:
    normalized = normalize_class_name(name)
    return normalized is not None and normalized.startswith(prefixes)


def load_classpath(paths: list[Path]) -> dict[str, object]:
    classes: dict[str, object] = {}
    for jar in paths:
        for name, info in load_classes(jar).items():
            classes.setdefault(name, info)
    return classes


def read_classpath(path: Path) -> list[Path]:
    entries = [Path(line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not entries:
        raise OSError(f"Empty classpath file: {path}")
    missing = [entry for entry in entries if not entry.is_file()]
    if missing:
        raise OSError(f"Missing classpath entries from {path}: {missing}")
    return entries


def analyze_platform_linkage(
    core_jar: Path,
    platform_classpath: list[Path],
    modern_platform_classpath: list[Path],
    prefixes: tuple[str, ...] = DEFAULT_PREFIXES,
) -> PlatformLinkageResult:
    core_classes = load_classes(core_jar)
    platform_classes = load_classpath(platform_classpath)
    modern_platform_classes = load_classpath(modern_platform_classpath)

    missing_classes: set[str] = set()
    missing_methods: set[MemberRef] = set()
    missing_fields: set[MemberRef] = set()
    checked_classes: set[str] = set()
    checked_members: set[MemberRef] = set()

    for core_class in core_classes.values():
        for raw_name in core_class.class_references:
            name = normalize_class_name(raw_name)
            if name is None or not name.startswith(prefixes):
                continue
            checked_classes.add(name)
            if name not in platform_classes and name in modern_platform_classes:
                missing_classes.add(name)

        for raw_reference in core_class.references:
            owner = normalize_class_name(raw_reference.owner)
            if owner is None or not owner.startswith(prefixes):
                continue

            reference = MemberRef(
                owner,
                raw_reference.name,
                raw_reference.descriptor,
                raw_reference.kind,
            )
            checked_members.add(reference)

            if owner not in platform_classes:
                if owner in modern_platform_classes:
                    missing_classes.add(owner)
                continue

            if resolves_member(
                platform_classes,
                owner,
                reference.name,
                reference.descriptor,
                reference.kind,
            ):
                continue

            # Methods such as Enum#ordinal, Object#equals, Audience#sendMessage,
            # or ObjectInputStream#readObject are inherited from dependencies that
            # are not bundled inside paper-api.jar. Only classify a floor-missing
            # member when the exact descriptor resolves inside the modern Paper API
            # that produced the Slimefun bytecode. This retains detection of modern
            # covariant overrides while avoiding external-inheritance false positives.
            if not resolves_member(
                modern_platform_classes,
                owner,
                reference.name,
                reference.descriptor,
                reference.kind,
            ):
                continue

            if reference.kind == "field":
                missing_fields.add(reference)
            else:
                missing_methods.add(reference)

    return PlatformLinkageResult(
        core_jar=str(core_jar),
        platform_classpath=[str(path) for path in platform_classpath],
        modern_platform_classpath=[str(path) for path in modern_platform_classpath],
        core_classes=len(core_classes),
        checked_class_references=len(checked_classes),
        checked_member_references=len(checked_members),
        missing_classes=sorted(missing_classes),
        missing_methods=sorted(missing_methods),
        missing_fields=sorted(missing_fields),
    )


def write_report(result: PlatformLinkageResult, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = result.to_json()
    (report_dir / "result.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (report_dir / "status.txt").write_text(
        ("PASS" if result.passed else "FAIL") + "\n", encoding="utf-8"
    )

    lines = [
        "## Platform binary linkage",
        "",
        f"**Result:** `{'PASS' if result.passed else 'FAIL'}`",
        "",
        f"Core classes inspected: **{result.core_classes}**",
        "",
        f"Bukkit/Paper class references checked: **{result.checked_class_references}**",
        "",
        f"Bukkit/Paper member references checked: **{result.checked_member_references}**",
    ]
    if result.missing_classes:
        lines.extend(["", "### Missing classes", ""])
        lines.extend(f"- `{name}`" for name in result.missing_classes)
    if result.missing_methods:
        lines.extend(["", "### Missing methods", ""])
        lines.extend(
            f"- `{ref.owner}.{ref.name}{ref.descriptor}`"
            for ref in result.missing_methods
        )
    if result.missing_fields:
        lines.extend(["", "### Missing fields", ""])
        lines.extend(
            f"- `{ref.owner}.{ref.name}:{ref.descriptor}`"
            for ref in result.missing_fields
        )
    (report_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("core_jar", type=Path)
    parser.add_argument("platform_classpath_file", type=Path)
    parser.add_argument("modern_platform_classpath_file", type=Path)
    parser.add_argument("report_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (args.core_jar, args.platform_classpath_file, args.modern_platform_classpath_file):
        if not path.is_file():
            print(f"Missing input: {path}", file=sys.stderr)
            return 2
    try:
        result = analyze_platform_linkage(
            args.core_jar.resolve(),
            read_classpath(args.platform_classpath_file.resolve()),
            read_classpath(args.modern_platform_classpath_file.resolve()),
        )
        write_report(result, args.report_dir.resolve())
    except (OSError, zipfile.BadZipFile, ClassFormatError) as error:
        print(f"Platform linkage instrumentation error: {error}", file=sys.stderr)
        return 2
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
