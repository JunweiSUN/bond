# Bond2Proto: Compiler-Backed Bond-to-Protobuf Migration

## Recommendation

Bond2Proto is a self-contained Windows command-line package for converting
Microsoft Bond IDL schemas into Protocol Buffers proto3 definitions. It is a
strong choice for teams that need repeatable, reviewable schema migration
without relying on an LLM to infer Bond syntax or invent conversion rules.

The package exposes a friendly `b2p.exe` command while keeping the bundled
Bond compiler, `gbc.exe`, private. It also includes the standard Bond IDL files
and configures their include path automatically.

## Why use Bond2Proto?

- **Compiler-backed parsing:** Bond schemas are parsed by the Bond compiler,
  not interpreted as free-form text.
- **Deterministic output:** The same input and options produce the same proto3
  schema, which makes automation and code review practical.
- **Explicit failures:** Unsupported Bond constructs cause a non-zero exit and
  a concrete error instead of being silently approximated.
- **Batch conversion:** A single command can process individual files, multiple
  files, or an entire directory tree.
- **Bundled dependencies:** `gbc.exe` and the standard `bond/core` IDL files
  travel with the Python package; users do not need to put `gbc.exe` on
  `PATH`.
- **Automation-friendly:** The CLI works in local scripts and CI pipelines and
  does not require a network call or transmit proprietary schemas externally.

## Requirements and installation

Bond2Proto 0.0.1 is distributed as a Windows x64 wheel and requires Python 3.9
or later.

```powershell
python -m pip install .\bond2proto-0.0.1-py3-none-win_amd64.whl
```

Installation creates `b2p.exe` in the active Python environment's Scripts
directory. The private `gbc.exe` remains under the installed `bond2proto`
package and is never added to `PATH`.

Verify the installation:

```powershell
b2p --version
b2p --help
```

## Basic usage

Convert one Bond schema:

```powershell
b2p -o .\generated .\schemas\catalog.bond
```

Convert several files:

```powershell
b2p -o .\generated .\schemas\catalog.bond .\schemas\orders.bond
```

Convert a directory tree:

```powershell
b2p -o .\generated .\schemas
```

Directory inputs are scanned recursively. Files with a `.bond` extension are
matched case-insensitively, sorted, and de-duplicated before compilation.

Add import paths and map a Bond namespace to a proto package:

```powershell
b2p `
  -i .\shared-idl `
  -n "company.catalog=company.catalog.v1" `
  -o .\generated `
  .\schemas
```

Open the directory containing the bundled Codex skill:

```powershell
b2p --open-skill
```

## Practical examples

Convert two schema groups with a shared import directory and explicit package
mappings:

```powershell
b2p `
  -i .\shared-idl `
  -n "company.catalog=company.catalog.v1" `
  -n "company.orders=company.orders.v1" `
  -o .\generated `
  .\catalog-schemas .\order-schemas
```

Use every available processor for a large directory tree:

```powershell
b2p -j -o .\generated .\schemas
```

Fail a PowerShell CI step when conversion or `protoc` validation fails:

```powershell
b2p -o .\generated .\schemas
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

protoc --proto_path=.\generated --descriptor_set_out=.\generated\schemas.pb .\generated\*.proto
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

## Command-line options

| Option | Description |
|---|---|
| `FILE_OR_DIR` | A Bond schema file or a directory to scan recursively. Multiple values are accepted. |
| `-h`, `--help` | Display the argparse-generated help and exit. |
| `-?` | Display help using the legacy `gbc`-compatible alias. |
| `-i DIR`, `--import-dir DIR` | Add an import search directory. May be repeated. |
| `-o DIR`, `--output-dir DIR` | Write generated `.proto` files to `DIR`. The default is the current directory. |
| `-n MAPPING`, `--namespace MAPPING` | Map `bond_namespace=proto_package`. May be repeated. |
| `-j [NUM]`, `--jobs [NUM]` | Run `NUM` jobs concurrently. Omit `NUM` to use all available processors. |
| `--open-skill` | Open the directory containing the packaged `SKILL.md` and exit. |
| `-V`, `--version` | Print both the Bond2Proto Python package version and the bundled Bond compiler version. |

## What happens when `b2p` runs?

1. `argparse` validates the command line.
2. File inputs are accepted directly; directory inputs are expanded into a
   stable list of `.bond` files.
3. `BOND_INCLUDE_PATH` is set to the absolute path of the packaged
   `bond/core` directory.
4. The packaged IDL root is added to the compiler import path.
5. The private `gbc.exe` is invoked by absolute path using its `protobuf`
   backend.
6. The compiler's exit code is returned to the caller.

## Bond2Proto versus direct LLM conversion

An LLM can be useful during a migration, but it should not be the only schema
translator. Bond2Proto and an LLM solve different parts of the problem.

| Area | Bond2Proto | Direct LLM conversion |
|---|---|---|
| Parsing | Uses the Bond compiler's parser and type model. | Infers syntax from prompt context and training data. |
| Conversion rules | Applies explicit, versioned type, field, enum, inheritance, and service mappings. | May vary between prompts, models, or runs. |
| Unsupported syntax | Fails with a non-zero exit and identifies constructs such as `wstring`, `set`, `nullable`, nested containers, generics, or unsupported defaults. | May silently approximate, omit, or rewrite unsupported constructs. |
| Field numbering | Applies the backend's deterministic ordinal-to-field-number rules. | Can accidentally renumber fields or introduce collisions. |
| Imports and namespaces | Resolves Bond imports through compiler search paths and applies explicit namespace mappings. | Often needs all related files pasted into the context and may guess package relationships. |
| Reproducibility | Suitable for scripts, CI, and repeatable large-scale runs. | Output can be nondeterministic and requires more manual review. |
| Privacy and availability | Runs locally without sending schemas to an external model. | May require uploading proprietary schema content and depends on model availability. |
| Error handling | Produces machine-detectable exit codes and compiler errors. | Usually produces prose that another tool or person must validate. |
| Migration judgment | Intentionally conservative; it rejects semantics it cannot represent safely. | Useful for proposing redesigns, compatibility layers, and manual alternatives. |

### Recommended migration workflow

Use Bond2Proto as the authoritative first-pass translator, then use an LLM as
an assistant around the compiler-backed result:

1. Run `b2p` and keep the exact command in source control or CI.
2. Treat every non-zero exit as a required migration decision.
3. Use an LLM to explain an unsupported feature and propose alternatives, not
   to hide or bypass the compiler error.
4. Review the generated API shape and validate it with `protoc`.
5. Add compatibility and integration tests before switching producers or
   consumers.

This approach combines deterministic translation with human and LLM-assisted
design work where an exact one-to-one mapping does not exist.

## Important limitations

- Generated proto3 schemas are **not wire-compatible** with existing Bond
  payloads. Existing serialized Bond data cannot be decoded as Protobuf merely
  because a schema was converted.
- Some Bond constructs have no safe proto3 equivalent and are rejected. These
  include `wstring`, `set`, `nullable`, `bonded`, nested containers, generics,
  type aliases, `required_optional`, custom non-default field defaults, and
  event methods.
- Bond inheritance is represented structurally through a `_base` field rather
  than native inheritance.
- A failed conversion may leave a partial `.proto` file. Always check the exit
  code and treat output from a failed run as invalid.
- Use `protoc` and application-level tests to validate the generated schemas
  before production adoption.

## Demo video script

### Demo goal

Show that Bond2Proto installs quickly, converts a file and a directory,
produces deterministic compiler-backed output, and rejects unsupported Bond
syntax instead of guessing.

Suggested duration: **4 minutes**.

### Demo preparation

Create a `demo` directory containing `schemas/catalog.bond`:

```bond
namespace demo.catalog

enum ProductStatus
{
    Unknown = 0,
    Active = 1,
    Retired = 2
}

struct ProductRequest
{
    1: string id;
}

struct Product
{
    1: string id;
    2: string name;
    3: ProductStatus status = Unknown;
    4: list<string> tags;
}

service CatalogService
{
    Product GetProduct(ProductRequest);
}
```

Also create `schemas/unsupported.bond` for the error demonstration:

```bond
namespace demo.catalog

struct UnsupportedExample
{
    1: wstring display_name;
}
```

### Shot list and narration

| Time | On screen | Narration |
|---|---|---|
| 00:00–00:20 | Title card: “Bond2Proto — Compiler-Backed Bond-to-Protobuf Migration” | “Migrating schema definitions is the kind of task where plausible output is not enough. Bond2Proto converts Bond IDL to proto3 by calling the Bond compiler itself, giving us deterministic output and explicit errors.” |
| 00:20–00:40 | Show the wheel, then run the installation command. | “Bond2Proto is distributed as a self-contained Windows Python wheel. Installing it creates the `b2p` command. The Bond compiler and standard Bond IDL files stay private inside the package, so we do not need to configure `gbc.exe` on PATH.” |
| 00:40–01:05 | Run `b2p --help` and briefly highlight the options and examples. | “The command accepts files or directories. We can select an output directory, add import paths, map namespaces, enable parallel jobs, or open the packaged Codex skill. The built-in examples cover the most common conversion patterns.” |
| 01:05–01:30 | Open `catalog.bond` in an editor and point to the enum, structs, list, and service. | “This sample contains an enum, two structs, a container field, and a service. These are parsed as Bond syntax rather than treated as unstructured text.” |
| 01:30–01:50 | Run `b2p -o .\generated .\schemas\catalog.bond`. | “A single command invokes the private compiler backend. A zero exit code tells us the conversion completed successfully.” |
| 01:50–02:20 | Open `generated/catalog.proto`; highlight `syntax = "proto3"`, package, messages, enum, repeated field, and RPC. | “The output contains deterministic proto3 declarations: Bond structs become messages, the list becomes a repeated field, the namespace becomes a package, and the service method becomes an RPC.” |
| 02:20–02:40 | Move `unsupported.bond` out temporarily, then run `b2p -o .\generated .\schemas` to demonstrate directory input. | “Directory mode recursively discovers Bond files, sorts them, removes duplicates, and passes the complete list to the compiler. This is convenient for repository-scale migrations and CI.” |
| 02:40–03:10 | Restore `unsupported.bond` and run `b2p -o .\generated .\schemas\unsupported.bond`. Show the non-zero exit and `wstring` error. | “Now for the most important difference from a direct LLM conversion. Proto3 has no wide-string type. Bond2Proto does not guess, silently narrow the field, or delete it. The compiler-backed backend stops and reports exactly which field cannot be represented.” |
| 03:10–03:30 | Show a split screen: compiler error on the left, an LLM chat on the right. | “This is where an LLM becomes useful: not as the authoritative translator, but as an assistant that explains the error and helps us choose an intentional redesign. The compiler remains the source of truth.” |
| 03:30–03:45 | Run `b2p --open-skill`; show the folder containing `SKILL.md`. | “The wheel also carries a Codex skill with the recommended conversion and validation workflow. The `--open-skill` option takes us directly to it.” |
| 03:45–04:00 | Closing slide with three bullets: deterministic, explicit failures, automation-ready. | “Bond2Proto gives us deterministic translation, explicit handling of unsupported syntax, and a workflow that scales from one file to CI. Use the compiler for correctness, and use an LLM where migration design genuinely requires judgment.” |

### Commands shown in the video

```powershell
py -m pip install .\bond2proto-0.0.1-py3-none-win_amd64.whl
b2p --help
b2p -o .\generated .\schemas\catalog.bond
b2p -o .\generated .\schemas
b2p -o .\generated .\schemas\unsupported.bond
b2p --open-skill
```

### Closing call to action

> Start with one representative Bond schema, inspect the generated proto3
> contract, and add the exact `b2p` command to source control. Scale to the
> full schema directory only after the field mappings and unsupported-feature
> decisions have been reviewed.
