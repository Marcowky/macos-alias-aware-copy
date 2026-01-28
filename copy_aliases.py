#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from typing import Optional

MDLS_BIN = "/usr/bin/mdls"
OSASCRIPT_BIN = "/usr/bin/osascript"

ALIAS_CONTENT_TYPE = "com.apple.alias-file"

RESOLVE_ALIAS_SCRIPT = """\
on run argv
    set theItem to POSIX file (item 1 of argv)
    tell application "Finder"
        set resolved to (original item of (theItem as alias)) as alias
        return POSIX path of resolved
    end tell
end run
"""


def run_cmd(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def run_osascript(script: str, args: list[str]) -> Optional[str]:
    cmd = [OSASCRIPT_BIN, "-e", script, "--"] + args
    result = run_cmd(cmd)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_alias_file(path: str) -> bool:
    result = run_cmd([MDLS_BIN, "-name", "kMDItemContentType", "-raw", path])
    if result.returncode != 0:
        return False
    return result.stdout.strip() == ALIAS_CONTENT_TYPE


def resolve_alias(path: str) -> Optional[str]:
    return run_osascript(RESOLVE_ALIAS_SCRIPT, [path])


def resolve_alias_chain(path: str, max_depth: int = 10) -> Optional[str]:
    current = path
    for _ in range(max_depth):
        if not is_alias_file(current):
            return current
        resolved = resolve_alias(current)
        if not resolved:
            return None
        if resolved == current:
            return current
        current = resolved
    return current


def ensure_dir(path: str) -> None:
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise ValueError(f"Destination exists and is not a directory: {path}")
        return
    os.makedirs(path)


def copy_file(src_path: str, dest_path: str, follow_symlinks: bool) -> None:
    parent = os.path.dirname(dest_path)
    if parent:
        ensure_dir(parent)
    shutil.copy2(src_path, dest_path, follow_symlinks=follow_symlinks)


def copy_directory(src_dir: str, dest_dir: str, verbose: bool) -> None:
    ensure_dir(dest_dir)
    for entry in os.scandir(src_dir):
        copy_item(entry.path, os.path.join(dest_dir, entry.name), verbose)


def ensure_target_extension(dest_path: str, target_path: str) -> str:
    if os.path.isdir(target_path):
        return dest_path
    target_ext = os.path.splitext(target_path)[1]
    if not target_ext:
        return dest_path
    if dest_path.lower().endswith(target_ext.lower()):
        return dest_path
    return dest_path + target_ext


def copy_target(src_path: str, dest_path: str, verbose: bool) -> None:
    if is_alias_file(src_path):
        resolved = resolve_alias_chain(src_path)
        if resolved:
            src_path = resolved
    if os.path.isdir(src_path):
        copy_directory(src_path, dest_path, verbose)
        return
    copy_file(src_path, dest_path, follow_symlinks=True)


def copy_item(src_path: str, dest_path: str, verbose: bool) -> None:
    if is_alias_file(src_path):
        target = resolve_alias_chain(src_path)
        if not target:
            print(f"warning: failed to resolve alias: {src_path}", file=sys.stderr)
            copy_file(src_path, dest_path, follow_symlinks=False)
            return
        if verbose:
            print(f"alias: {src_path} -> {target}")
        dest_path = ensure_target_extension(dest_path, target)
        copy_target(target, dest_path, verbose)
        return
    if os.path.isdir(src_path) and not os.path.islink(src_path):
        copy_directory(src_path, dest_path, verbose)
        return
    copy_file(src_path, dest_path, follow_symlinks=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a macOS folder to another folder, replacing alias files with"
            " their targets while keeping the alias names and target extensions."
        )
    )
    parser.add_argument("source", help="Source directory on macOS")
    parser.add_argument("destination", help="Destination directory")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print each alias resolution",
    )
    return parser.parse_args()


def main() -> int:
    if sys.platform != "darwin":
        print("error: this script only supports macOS", file=sys.stderr)
        return 1

    args = parse_args()
    source = os.path.abspath(args.source)
    destination = os.path.abspath(args.destination)

    if not os.path.isdir(source):
        print(f"error: source is not a directory: {source}", file=sys.stderr)
        return 1

    source_real = os.path.realpath(source)
    destination_real = os.path.realpath(destination)
    if source_real == destination_real:
        print("error: source and destination are the same directory", file=sys.stderr)
        return 1
    if os.path.commonpath([source_real, destination_real]) == source_real:
        print(
            "error: destination cannot be inside the source directory",
            file=sys.stderr,
        )
        return 1

    ensure_dir(destination)
    copy_directory(source, destination, args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
