#!/usr/bin/env python3
"""Synthetic regression coverage for the Bukkit/Paper floor linkage checker."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from check_platform_binary_linkage import analyze_platform_linkage


def run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(command)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def write_java(root: Path, package: str, class_name: str, body: str) -> Path:
    path = root / Path(package.replace(".", "/")) / f"{class_name}.java"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"package {package};\n{body}\n", encoding="utf-8")
    return path


def compile_jar(
    work: Path,
    name: str,
    sources: list[Path],
    classpath: Path | list[Path] | None = None,
) -> Path:
    classes = work / f"{name}-classes"
    classes.mkdir(parents=True)
    command = ["javac", "--release", "21", "-d", str(classes)]
    if classpath:
        entries = classpath if isinstance(classpath, list) else [classpath]
        command.extend(["-classpath", os.pathsep.join(str(entry) for entry in entries)])
    command.extend(str(source) for source in sources)
    run(command, work)
    jar = work / f"{name}.jar"
    run(["jar", "--create", "--file", str(jar), "-C", str(classes), "."], work)
    return jar


def main() -> int:
    if not shutil.which("javac") or not shutil.which("jar"):
        print("Platform linkage verification requires javac and jar.", file=sys.stderr)
        return 1

    try:
        with tempfile.TemporaryDirectory(prefix="slimefun-platform-linkage-") as raw:
            work = Path(raw)

            base_source = write_java(
                work / "base-src",
                "org.bukkit.event",
                "BaseEvent",
                "public class BaseEvent { public Object getEntity() { return null; } }",
            )
            floor_event_source = write_java(
                work / "floor-src",
                "org.bukkit.event",
                "PotionEvent",
                "public class PotionEvent extends BaseEvent {}",
            )
            floor_api = compile_jar(work, "floor-api", [base_source, floor_event_source])

            modern_base_source = write_java(
                work / "modern-base-src",
                "org.bukkit.event",
                "BaseEvent",
                "public class BaseEvent { public Object getEntity() { return null; } }",
            )
            modern_event_source = write_java(
                work / "modern-src",
                "org.bukkit.event",
                "PotionEvent",
                "public class PotionEvent extends BaseEvent { "
                "@Override public String getEntity() { return null; } }",
            )
            modern_api = compile_jar(
                work, "modern-api", [modern_base_source, modern_event_source]
            )

            unsafe_source = write_java(
                work / "unsafe-src",
                "example.core",
                "UnsafeListener",
                "public class UnsafeListener { "
                "public Object read(org.bukkit.event.PotionEvent event) { return event.getEntity(); } }",
            )
            unsafe_core = compile_jar(work, "unsafe-core", [unsafe_source], modern_api)
            unsafe = analyze_platform_linkage(unsafe_core, [floor_api], [modern_api])
            if unsafe.passed:
                raise AssertionError("Covariant-return floor mismatch was not detected")
            if not any(
                ref.owner == "org/bukkit/event/PotionEvent"
                and ref.name == "getEntity"
                and ref.descriptor == "()Ljava/lang/String;"
                for ref in unsafe.missing_methods
            ):
                raise AssertionError(f"Expected covariant getEntity mismatch: {unsafe.to_json()}")

            safe_source = write_java(
                work / "safe-src",
                "example.core",
                "SafeListener",
                "public class SafeListener { "
                "public Object read(org.bukkit.event.PotionEvent event) { "
                "return ((org.bukkit.event.BaseEvent) event).getEntity(); } }",
            )
            safe_core = compile_jar(work, "safe-core", [safe_source], modern_api)
            safe = analyze_platform_linkage(safe_core, [floor_api], [modern_api])
            if not safe.passed:
                raise AssertionError(f"Stable inherited descriptor unexpectedly failed: {safe.to_json()}")

            audience_source = write_java(
                work / "audience-src",
                "net.kyori.adventure.audience",
                "Audience",
                "public interface Audience { default void sendMessage(String message) {} }",
            )
            adventure = compile_jar(work, "adventure-api", [audience_source])
            floor_sender_source = write_java(
                work / "floor-sender-src",
                "org.bukkit.command",
                "CommandSender",
                "public interface CommandSender extends net.kyori.adventure.audience.Audience {}",
            )
            floor_sender = compile_jar(work, "floor-sender", [floor_sender_source], adventure)
            modern_sender_source = write_java(
                work / "modern-sender-src",
                "org.bukkit.command",
                "CommandSender",
                "public interface CommandSender extends net.kyori.adventure.audience.Audience { "
                "@Override default void sendMessage(String message) {} }",
            )
            modern_sender = compile_jar(work, "modern-sender", [modern_sender_source], adventure)
            sender_user_source = write_java(
                work / "sender-user-src",
                "example.core",
                "SenderUser",
                "public class SenderUser { public void send(org.bukkit.command.CommandSender sender) { "
                "sender.sendMessage(\"hello\"); } }",
            )
            sender_user = compile_jar(
                work,
                "sender-user",
                [sender_user_source],
                [modern_sender, adventure],
            )
            inherited_external = analyze_platform_linkage(
                sender_user,
                [floor_sender, adventure],
                [modern_sender, adventure],
            )
            if not inherited_external.passed:
                raise AssertionError(
                    "External inherited platform member was misclassified: "
                    f"{inherited_external.to_json()}"
                )

        print("Platform binary-linkage checker regression verification passed.")
        return 0
    except (AssertionError, OSError) as error:
        print(f"Platform binary-linkage checker verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
