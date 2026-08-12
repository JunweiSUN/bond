"""Entry point for the bundled Bond-to-Protobuf compiler."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from . import __version__


_PACKAGE_DIR = Path(__file__).resolve().parent
_GBC_EXE = _PACKAGE_DIR / "bin" / "gbc.exe"
_BOND_CORE_DIR = _PACKAGE_DIR / "bond" / "core"
_SKILL_DIR = _PACKAGE_DIR / "skill"
_SKILL_FILE = _SKILL_DIR / "SKILL.md"

_EXAMPLES = r"""examples:
  Convert one schema:
    b2p -o proto-output schema.bond

  Convert several schemas or recursively scan a directory:
    b2p -o proto-output schemas\catalog.bond schemas\orders.bond
    b2p -o proto-output schemas

  Resolve project imports and map a Bond namespace:
    b2p -i shared-idl -n "company.catalog=company.catalog.v1" -o proto-output schemas

  Use all available processors:
    b2p -j -o proto-output schemas
"""


def _normalize_optional_jobs(args: Sequence[str]) -> list[str]:
    """Translate a value-less -j/--jobs to the compiler's default value."""

    normalized: list[str] = []
    index = 0
    while index < len(args):
        argument = args[index]
        if argument == "--":
            normalized.extend(args[index:])
            break
        if argument in {"-j", "--jobs"}:
            next_index = index + 1
            if next_index < len(args):
                try:
                    int(args[next_index])
                except ValueError:
                    normalized.append(f"{argument}=0")
                    index += 1
                    continue
                normalized.extend((argument, args[next_index]))
                index += 2
                continue
            normalized.append(f"{argument}=0")
            index += 1
            continue
        normalized.append(argument)
        index += 1
    return normalized


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="b2p",
        description="Convert Bond IDL schemas to Protocol Buffers proto3 files.",
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument("-?", action="help", help="Show this help message and exit")
    parser.add_argument(
        "-i",
        "--import-dir",
        action="append",
        default=[],
        metavar="DIR",
        help="Add a directory to the import search path (repeatable)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        help="Write generated files to DIR (default: current directory)",
    )
    parser.add_argument(
        "-n",
        "--namespace",
        action="append",
        default=[],
        metavar="MAPPING",
        help="Map bond_namespace=proto_package (repeatable)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        metavar="[NUM]",
        help="Run NUM jobs simultaneously; omit NUM to use all processors",
    )
    parser.add_argument(
        "--open-skill",
        action="store_true",
        help="Open the directory containing the bundled SKILL.md and exit",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="Print the Bond2Proto and bundled Bond compiler versions",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        metavar="FILE_OR_DIR",
        help="Bond schema file or directory to convert; directories are scanned recursively",
    )
    return parser


def _expand_inputs(inputs: Sequence[str], parser: argparse.ArgumentParser) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()

    for value in inputs:
        path = Path(value).expanduser()
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(
                (
                    candidate
                    for candidate in path.rglob("*")
                    if candidate.is_file() and candidate.suffix.lower() == ".bond"
                ),
                key=lambda candidate: str(candidate).lower(),
            )
            if not candidates:
                parser.error(f"directory contains no .bond files: {value}")
        else:
            parser.error(f"input path does not exist: {value}")

        for candidate in candidates:
            resolved = str(candidate.resolve())
            key = os.path.normcase(resolved)
            if key not in seen:
                seen.add(key)
                expanded.append(resolved)

    return expanded


def _open_skill_directory() -> int:
    if not _SKILL_FILE.is_file():
        print(f"b2p: bundled skill not found: {_SKILL_FILE}", file=sys.stderr)
        return 1

    try:
        os.startfile(str(_SKILL_DIR))
    except OSError as error:
        print(f"b2p: failed to open skill directory: {error}", file=sys.stderr)
        return 1
    return 0


def _print_versions() -> int:
    if not _GBC_EXE.is_file():
        print(f"b2p: bundled compiler not found: {_GBC_EXE}", file=sys.stderr)
        return 1

    try:
        result = subprocess.run(
            [str(_GBC_EXE), "--numeric-version"],
            capture_output=True,
            text=True,
        )
    except OSError as error:
        print(f"b2p: failed to start bundled compiler: {error}", file=sys.stderr)
        return 1

    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        if error_output:
            print(error_output, file=sys.stderr)
        return result.returncode

    print(f"Bond2Proto {__version__}")
    print(f"Bond Compiler {result.stdout.strip()}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bundled ``gbc protobuf`` command with the supplied arguments."""

    args = list(sys.argv[1:] if argv is None else argv)
    parser = _create_parser()
    if not args:
        parser.print_help()
        return 0
    options = parser.parse_args(_normalize_optional_jobs(args))

    if options.open_skill:
        return _open_skill_directory()
    if options.version:
        return _print_versions()

    if not options.inputs:
        parser.error("at least one FILE_OR_DIR is required")
    files = _expand_inputs(options.inputs, parser)

    if not _GBC_EXE.is_file():
        print(f"b2p: bundled compiler not found: {_GBC_EXE}", file=sys.stderr)
        return 1
    if not _BOND_CORE_DIR.is_dir():
        print(f"b2p: bundled Bond IDL directory not found: {_BOND_CORE_DIR}", file=sys.stderr)
        return 1

    bond_core = str(_BOND_CORE_DIR)
    os.environ["BOND_INCLUDE_PATH"] = bond_core

    command = [str(_GBC_EXE), "protobuf", "-i", str(_PACKAGE_DIR)]
    for import_dir in options.import_dir:
        command.extend(("-i", import_dir))
    if options.output_dir is not None:
        command.extend(("-o", options.output_dir))
    for namespace in options.namespace:
        command.extend(("-n", namespace))
    if options.jobs is not None:
        command.append(f"--jobs={options.jobs}")
    command.extend(files)

    try:
        return subprocess.run(command).returncode
    except OSError as error:
        print(f"b2p: failed to start bundled compiler: {error}", file=sys.stderr)
        return 1
