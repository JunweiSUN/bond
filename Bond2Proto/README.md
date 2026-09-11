# Bond2Proto

`Bond2Proto` packages the Bond compiler and the standard Bond IDL files as a
self-contained Windows command-line tool.

## Installation

```powershell
python -m pip install bond2proto-0.0.1-py3-none-win_amd64.whl
```

Installation creates `b2p.exe` in Python's scripts directory. The bundled
`gbc.exe` remains private to the package and is not added to `PATH`.

## Usage

`b2p` accepts the same arguments as `gbc protobuf`:

```powershell
b2p -o proto_output schema.bond
b2p -o proto_output schemas\catalog.bond schemas\orders.bond
b2p -o proto_output path\to\schemas
b2p -i additional_idl -n "bond.namespace=proto.package" schema.bond
b2p -j -o proto_output path\to\schemas
b2p --help
b2p --open-skill
```

Each positional argument may be a file or a directory. Directories are scanned
recursively, and every file whose extension is `.bond` (case-insensitive) is
passed to the compiler. Expanded paths are sorted and de-duplicated.

Use `b2p --open-skill` to open the directory containing the bundled Codex
`SKILL.md` in Windows File Explorer.

Supported options include:

- `-o DIR`, `--output-dir=DIR`
- `-i DIR`, `--import-dir=DIR`
- `-n MAPPING`, `--namespace=MAPPING`
- `-j NUM`, `--jobs=NUM`
- `--help`
- `-V`, `--version` (prints both the Bond2Proto package version and bundled Bond compiler version)

Before launching the bundled compiler, `b2p` sets `BOND_INCLUDE_PATH` to the
absolute path of its bundled `bond/core` directory. It also supplies the
package data root as an import directory so imports such as
`bond/core/bond.bond` can be resolved.
