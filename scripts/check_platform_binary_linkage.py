#!/usr/bin/env python3
"""Check a compiled Slimefun JAR against the supported Bukkit/Paper API floor.

The production core is compiled against the modern Paper API. JVM member references
can therefore bind to covariant overrides or other descriptors that do not exist on
the supported 1.21.11 floor even when the same Java source also compiles there.

This checker inspects the production JAR's constant-pool references and resolves every
Bukkit/Paper class, method, and field against the real floor API JAR.
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

DEFAULT_PREFIXES = ("org/bukkit/", "io/papermc/paper/")


@dataclass
class PlatformLinkageResult:
    core_jar: str
    platform_api_jar: str
    modern_platform_api_jar: str
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
            "platform_api_jar": self.platform_api_jar,
            "modern_platform_api_jar": self.modern_platform_api_jar,
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


def analyze_platform_linkage(
    core_jar: Path,
    platform_api_jar: Path,
    modern_platform_api_jar: Path,
    prefixes: tuple[str, ...] = DEFAULT_PREFIXES,
) -> PlatformLinkageResult:
    core_classes = load_classes(core_jar)
    platform_classes = load_classes(platform_api_jar)
    modern_platform_classes = load_classes(modern_platform_api_jar)

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
        platform_api_jar=str(platform_api_jar),
        modern_platform_api_jar=str(modern_platform_api_jar),
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
    parser.add_argument("platform_api_jar", type=Path)
    parser.add_argument("modern_platform_api_jar", type=Path)
    parser.add_argument("report_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (args.core_jar, args.platform_api_jar, args.modern_platform_api_jar):
        if not path.is_file():
            print(f"Missing JAR: {path}", file=sys.stderr)
            return 2
    try:
        result = analyze_platform_linkage(
            args.core_jar.resolve(),
            args.platform_api_jar.resolve(),
            args.modern_platform_api_jar.resolve(),
        )
        write_report(result, args.report_dir.resolve())
    except (OSError, zipfile.BadZipFile, ClassFormatError) as error:
        print(f"Platform linkage instrumentation error: {error}", file=sys.stderr)
        return 2
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
