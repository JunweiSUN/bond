# Bond-to-Protobuf Compiler Backend

The Bond compiler (`gbc`) includes a `protobuf` backend that converts Bond IDL
(`.bond`) schema files into Protocol Buffers proto3 (`.proto`) files. This
enables migration from Bond to Protocol Buffers by automatically translating
schemas.

## Usage

```
gbc protobuf [OPTIONS] <schema.bond> [schema2.bond ...]
```

### Options

| Option | Description |
|--------|-------------|
| `-o DIR` | Output directory for generated `.proto` files (default: `.`) |
| `-i DIR` | Add directory to import search path (can be repeated) |
| `-n MAPPING` | Custom namespace mapping in the form `bond_namespace=proto_package` |
| `-j NUM` | Run NUM jobs simultaneously |
| `--no-banner` | Omit the generated-code banner at the top of output files |

### Example

```bash
# Convert a single schema
gbc protobuf -o proto_output/ myschema.bond

# Convert with import paths
gbc protobuf -i schemas/common -o proto_output/ schemas/service.bond

# Convert with namespace mapping
gbc protobuf -n "com.example.bond=com.example.proto" -o proto_output/ myschema.bond

# Convert multiple files
gbc protobuf -o proto_output/ schemas/*.bond
```

## Data Type Mappings

### Primitive Types

| Bond Type | Proto3 Type | Notes |
|-----------|-------------|-------|
| `bool` | `bool` | |
| `int8` | `int32` | Proto3 has no 8-bit integer; widened to 32-bit |
| `int16` | `int32` | Proto3 has no 16-bit integer; widened to 32-bit |
| `int32` | `int32` | |
| `int64` | `int64` | |
| `uint8` | `uint32` | Proto3 has no 8-bit unsigned; widened to 32-bit |
| `uint16` | `uint32` | Proto3 has no 16-bit unsigned; widened to 32-bit |
| `uint32` | `uint32` | |
| `uint64` | `uint64` | |
| `float` | `float` | |
| `double` | `double` | |
| `string` | `string` | |
| `blob` | `bytes` | |

### Container Types

| Bond Type | Proto3 Type | Notes |
|-----------|-------------|-------|
| `list<T>` | `repeated T` | Element `T` must not be a container (no nesting) |
| `vector<T>` | `repeated T` | Element `T` must not be a container (no nesting) |
| `map<K, V>` | `map<K, V>` | Key must be scalar or string; value must not be a container |

### Struct and Enum

| Bond Type | Proto3 Type | Notes |
|-----------|-------------|-------|
| `struct` | `message` | |
| `enum` | `enum` | If first constant ≠ 0, a sentinel `ENUMNAME_UNSPECIFIED = 0` is prepended |

### Field Modifiers

| Bond Modifier | Proto3 Behavior |
|---------------|-----------------|
| `optional` (default) | Regular proto3 field (implicit default optionality) |
| `required` | Regular proto3 field (proto3 does not distinguish required) |
| Fields with `nothing` default (`BT_Maybe`) | `optional` keyword (proto3 explicit presence) |

### Services

| Bond Construct | Proto3 Construct |
|----------------|------------------|
| `Result Method(Param)` | `rpc Method(Param) returns (Result)` |
| `stream Result Method(Param)` | `rpc Method(Param) returns (stream Result)` |
| `Result Method(stream Param)` | `rpc Method(stream Param) returns (Result)` |
| `stream Result Method(stream Param)` | `rpc Method(stream Param) returns (stream Result)` |
| `void` input or result | `google.protobuf.Empty` (auto-imported) |

## Struct Inheritance

Bond supports single struct inheritance. Proto3 has no inheritance. The
compiler handles this by embedding the base struct as a field named `_base`
in the derived message:

**Bond:**
```
struct Base {
    0: string name;
}

struct Derived : Base {
    0: int32 age;
}
```

**Generated Proto3:**
```protobuf
message Base {
    string name = 1;
}

message Derived {
    Base _base = 2;
    int32 age = 1;
}
```

The `_base` field is assigned a field number one past the highest field number
in the derived struct.

## Field Number Mapping

Proto3 requires field numbers to be ≥ 1, but Bond ordinals can start from 0.
The compiler handles this automatically:

- **If any field in a struct has ordinal 0:** all field numbers are offset by
  +1 (Bond ordinal 0 → proto field 1, ordinal 1 → field 2, etc.)
- **If all fields have ordinals ≥ 1:** field numbers are kept as-is.

## Namespace / Package Mapping

The Bond namespace is mapped to a proto3 `package` declaration using
dot-separated notation:

```
namespace com.example.myservice
```

becomes:

```protobuf
package com.example.myservice;
```

Custom namespace mappings can be specified with the `-n` flag.

## Import Mapping

Bond `import` statements are translated to proto3 `import` statements with
the file extension changed from `.bond` to `.proto`:

```
import "common/types.bond"
```

becomes:

```protobuf
import "common/types.proto";
```

If any service method uses `void` for input or result, the compiler
automatically adds:

```protobuf
import "google/protobuf/empty.proto";
```

## Unsupported Features

The following Bond features have no protobuf equivalent. The compiler will
**abort with an error** if any of these are encountered:

### Unsupported Types

| Feature | Reason |
|---------|--------|
| `wstring` | Proto3 has no wide string type |
| `set<T>` | Proto3 has no set type |
| `nullable<T>` | Proto3 has no nullable wrapper |
| `bonded<T>` | Proto3 has no lazy deserialization concept |
| `bond_meta::name` | Bond-specific metadata type |
| `bond_meta::full_name` | Bond-specific metadata type |

### Unsupported Containers

| Feature | Reason |
|---------|--------|
| Nested containers (e.g. `list<list<T>>`, `map<K, list<V>>`) | Proto3 `repeated` and `map` cannot be nested |

### Unsupported Declarations

| Feature | Reason |
|---------|--------|
| Generic structs (`struct Foo<T>`) | Proto3 has no generics / templates |
| Generic services (`service Foo<T>`) | Proto3 has no generics / templates |
| Type aliases (`using Foo = bar`) | Proto3 has no type alias mechanism |

### Unsupported Modifiers and Defaults

| Feature | Reason |
|---------|--------|
| `required_optional` modifier | No proto3 equivalent |
| Non-default explicit default values (e.g. `int32 x = 42`) | Proto3 does not support custom field defaults in `.proto` syntax |

Note: Enum default values (required by Bond for enum fields) are accepted
since proto3 will use its own default (0) regardless.

### Unsupported Service Features

| Feature | Reason |
|---------|--------|
| `nothing` event methods | Proto3 has no fire-and-forget concept |

### Silently Skipped

| Feature | Behavior |
|---------|----------|
| Forward declarations | Skipped (proto3 does not need them) |
| Custom attributes | Not emitted (proto3 options are not generated) |

## Enum Sentinel Values

Proto3 requires the first enum value to be 0. If a Bond enum's first constant
is not 0, the compiler inserts a sentinel value:

**Bond:**
```
enum Status {
    Active = 1,
    Inactive = 2
}
```

**Generated Proto3:**
```protobuf
enum Status {
    STATUS_UNSPECIFIED = 0;
    Active = 1;
    Inactive = 2;
}
```

If the first constant is already 0, no sentinel is added.

## Limitations

- **Not wire-compatible.** The generated `.proto` files define an equivalent
  schema but do not produce wire-compatible serialization. Data serialized
  with Bond cannot be deserialized using the generated proto3 schema.
- **Field number offset.** When Bond ordinals start from 0, the +1 offset
  changes field numbers compared to the original Bond ordinals.
- **Inheritance is structural, not semantic.** The `_base` field embedding is
  a structural approximation; proto3 consumers must explicitly access
  `_base.field` rather than accessing inherited fields directly.
- **Custom attributes are dropped.** Bond attributes are not translated to
  proto3 options.

## Complete Example

**Input (`example.bond`):**
```
namespace example

enum Priority {
    Low,
    Medium,
    High = 10
}

struct Address {
    0: string street;
    1: string city;
    2: int32 zip_code;
}

struct Person : Address {
    0: required string name;
    1: int32 age;
    2: Priority priority = Low;
    3: list<string> tags;
    4: map<string, int32> scores;
    5: blob data;
}

service PersonService {
    Person GetPerson(Address);
    void SavePerson(Person);
    stream Person ListPeople(Address);
}
```

**Output (`example.proto`):**
```protobuf
syntax = "proto3";

package example;

import "google/protobuf/empty.proto";

enum Priority {
    Low = 0;
    Medium = 1;
    High = 10;
}

message Address {
    string street = 1;
    string city = 2;
    int32 zip_code = 3;
}

message Person {
    Address _base = 7;
    string name = 1;
    int32 age = 2;
    Priority priority = 3;
    repeated string tags = 4;
    map<string, int32> scores = 5;
    bytes data = 6;
}

service PersonService {
    rpc GetPerson(Address) returns (Person);
    rpc SavePerson(Person) returns (google.protobuf.Empty);
    rpc ListPeople(Address) returns (stream Person);
}
```
