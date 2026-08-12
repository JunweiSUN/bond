---
name: bond2proto
description: Convert Bond IDL files or directory trees to Protocol Buffers proto3 with the Bond2Proto b2p command. Use when the user asks to generate, validate, or troubleshoot .proto output from .bond schemas; do not use for general protobuf authoring or changes to the Bond compiler itself.
---

# Bond2Proto

Use the installed `b2p` command rather than invoking `gbc.exe` directly. The
package keeps `gbc.exe` private, sets `BOND_INCLUDE_PATH` to its bundled
`bond/core` directory, and adds the bundled IDL root to the compiler import
search path.

## Convert schemas

- Pass one or more `.bond` files or directories to `b2p`.
- A directory is scanned recursively for `.bond` files, case-insensitively;
  discovered paths are sorted and de-duplicated.
- Preserve any output directory, import directories, namespace mappings, job
  count, and input ordering supplied by the user.
- Use `b2p --help` for the installed command's authoritative option syntax.

Examples:

```powershell
# Convert one schema.
b2p -o proto-output schema.bond

# Convert several schemas or recursively scan a directory.
b2p -o proto-output schemas\catalog.bond schemas\orders.bond
b2p -o proto-output schemas

# Resolve project imports and map a Bond namespace to a proto package.
b2p -i additional-idl -n "bond.namespace=proto.package" -o proto-output schemas

# Use all available processors.
b2p -j -o proto-output schemas
```

Do not add the bundled `gbc.exe` to `PATH`. Do not replace the automatically
configured Bond include path with a machine-specific path.

## Verify output

Check the process exit code and confirm each expected `.proto` file exists.
When `protoc` is available, compile the generated files to a descriptor set to
catch syntax and import errors. Account for `google/protobuf/empty.proto` when
services use `void`.

Treat CRLF-versus-LF differences on Windows as formatting-only after verifying
that normalized content is identical. A failed conversion can leave a partial
`.proto` file, so do not present output from a failed run as valid.

Remember that generated schemas are not wire-compatible with existing Bond
payloads. Report unsupported Bond constructs from `b2p` as conversion limits;
do not silently rewrite their semantics.
