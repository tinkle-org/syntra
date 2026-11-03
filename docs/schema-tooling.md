# Schema tooling

This guide describes schema checks and reproducible type generation.
Protocol representation and validation are defined by the
[IDL](../proto/syntra/v1/) and [wire format](../specifications/wire-format.md).

## Schema source and checks

The schema source is `proto/syntra/v1/`. [buf.yaml](../buf.yaml) uses Buf v2
with one module rooted at `proto`, `STANDARD` lint and `FILE` breaking checks,
without exceptions or a registry identity. All imports resolve inside that
module; there are no external schema dependencies or `buf.lock`.
`session.proto` and `capabilities.proto` declare no messages or enums.

The validation toolchain is Buf **1.59.0** and Python **3.14**. The fixture
parser requires PyYAML **6.0.3**, pinned identically in CI.
From the repository root:

```sh
python3 -m pip install pyyaml==6.0.3
python3 scripts/validate-schema.py
```

The script checks the exact Buf version, then runs:

```sh
buf format --diff --exit-code
buf lint
buf build
buf breaking --against compatibility/v1-initial/image.json
python3 -m unittest discover -s tests/schema -p 'test_*.py' -v
```

The [schema tests](../tests/schema/test_schema.py) build a temporary
descriptor set, verify archived descriptor hashes, compare declarations,
check package/options/imports and reservations, decode shared fixtures,
check requirement references in proto comments, and exercise a negative
renumbering fixture. They also check the recovery-notification wrappers
and scalar-merge fixtures against the actual IDL. Temporary descriptor
files are cleaned up; schema sources and baseline archives are not rewritten.

The `FILE` gate uses the committed
[initial baseline](../compatibility/v1-initial/README.md). A separate `WIRE`
audit and expected `FILE` differences against `historical.json` are tested;
that archive does not replace the initial `FILE` baseline. Keep descriptor
layouts in separate files rather than loading both into one descriptor pool.
Baseline replacement is a reviewed change, not an automatic repair for a
failing check.

These checks cover schema declarations and fixtures. The current validator
does not generate language types, compile them, or execute network protocol
behavior. Repository-wide document and fixture checks run separately:

```sh
python3 scripts/validate-repo.py all
```

## Pinned generation inputs

Consumers pin an exact schema commit or release tag, the generator version
**and revision**, and their language runtime and dependency lockfile. The
recorded generation settings are:

| Component | Pin |
|---|---|
| Buf CLI | 1.59.0 |
| Rust generator | `buf.build/community/neoeinstein-prost:v0.4.0`, revision 1 |
| Rust runtime | `prost = "=0.13.5"` |
| Go generator | `buf.build/protocolbuffers/go:v1.36.6`, revision 1, `paths=source_relative` |
| Go runtime / language floor | `google.golang.org/protobuf v1.36.6` / Go 1.22 |

These are reproducibility settings, not latest-version recommendations or
a claim that generation was executed by the schema validator. There is no
`buf.gen.yaml` in this repository. To generate from a checkout at the pinned
schema revision, run from its root with an explicit inline template:

```sh
buf generate --template '{"version":"v2","plugins":[{"remote":"buf.build/community/neoeinstein-prost:v0.4.0","revision":1,"out":".tmp/schema-types/rust"},{"remote":"buf.build/protocolbuffers/go:v1.36.6","revision":1,"out":".tmp/schema-types/go","opt":"paths=source_relative"}]}'
```

This command writes disposable output under `.tmp/schema-types/`. Consumers
can set the output directories in their own templates. No separate `protoc`
invocation or managed-mode override is used. Generated output is not
hand-edited or committed here. Remote generators receive schema descriptors
and comments, never production payloads or credentials; generation requires
access to and trust in those remote plugins.

## Compatibility when updating pins

Check binary representation, generated source compatibility, and protocol
behavior separately. Field/tag/type/presence/oneof/enum/reservation checks
cover representation; `FILE` checks also cover owning files, imports,
packages and options. Source moves or option changes can break generated
consumers despite unchanged binary encoding. In particular, the current
`go_package` option is fixed by the initial baseline and asserted by the
schema tests; direct generation preserves it.

Upgrades regenerate consumer types and rerun compilation, codec tests and
relevant protocol checks with the new pins. A successful Buf check alone
does not establish protocol behavior. New external schema imports need
immutable provenance and dependency locking; lint/breaking exceptions and
baseline changes need explicit review rather than silently weakened checks.
