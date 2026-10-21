# Schema generation and validation

Status: development tooling; not a protocol conformance claim. See
[reference](reference.md), [compatibility](compatibility.md), and
[RFC 0001](../../rfcs/0001-public-idl-layout.md) for the recorded layout
decision and remaining behavioral blockers.

## Pinned generators and toolchains

| Component | Pin | Role |
|---|---|---|
| Buf CLI | **1.59.0** | v2 module/compiler, STANDARD lint and FILE gate |
| Rust generator | `buf.build/community/neoeinstein-prost:v0.4.0`, **revision 1** | Message/enum types, no networking or gRPC |
| Go generator | `buf.build/protocolbuffers/go:v1.36.6`, **revision 1** | Message/enum types, `paths=source_relative` |
| Rust toolchain (workspace) | **1.88**, minimal profile | Workspace crates tests; see `repo-validation.yml` and `release.yml` pins |
| Rust toolchain (schema isolated tests) | **1.85.1**, minimal profile | `tests/schema/rust` override; see standalone commands below |
| Rust runtime | `prost = "=0.13.5"` | Runtime/derive alignment; transitive dependencies locked in workspace `Cargo.lock` |
| Rust test JSON parser | `serde_json = "=1.0.140"` | Shared fixture reader only |
| Go runtime | `google.golang.org/protobuf v1.36.6` | Bindings module lockfile; checksums in `bindings/go/go.sum` |
| Go toolchain tested | **1.26.4** | `go.mod` language floor is 1.22; older toolchains have not been tested here |
| Python tested | **3.14** | Validator tooling (`pyyaml`); see workflow `setup-python` pins |

Versions are deliberate pins, not claims to be latest. The Prost plugin's
published dependency metadata permits the 0.13 line. Using runtime 0.13.1
with a resolved derive 0.13.5 failed compilation during verification;
runtime 0.13.5 plus the checked-in lockfile is the tested combination.
Tool upgrades are reviewed separately and rerun both language tests.

The checked-in `buf.gen.yaml` pins the committed `crates/` +
`bindings/go/` generation (see `docs/schema-registry.md` §11).
`scripts/validate-schema.py` writes an equivalent pinned template into
the ignored `.tmp/` directory at validation time, so the pins above
remain the single source of truth for versions and revisions. Remote
generation uses BSR-hosted plugins for byte-identical output only; it
never pushes schemas and requires no registry identity (`buf.yaml` has
no `name:`). It needs HTTPS access to those public generators, not
locally installed Rust/Go generator binaries. Schema descriptors,
including comments, are submitted to those public generators: use only
public schema sources, never production payloads or credentials. No
floating `latest`, private plugin, or unpinned fallback is configured.
Generator availability/trust is still a dependency; pins do not make
remote generation an offline build or attest the service's execution
environment.

Buf supplies the schema compiler. There is **no external `protoc` import
or binary dependency** in this workflow; the installed `protoc 35.1` was
not used. There are no external `.proto` imports, so no `buf.lock` dependency
lockfile is required. Schema imports are all `syntra/v1/*.proto`.

Install the exact Buf CLI release using the official
[installation guide](https://buf.build/docs/cli/installation/), and check
`buf --version` prints `1.59.0`. Install Rust 1.88 for the workspace
through rustup and keep Rust 1.85.1 available for the isolated
`tests/schema/rust` suite via its `rust-toolchain.toml` override, and use
Go 1.26.4 (or `GOTOOLCHAIN=go1.26.4`). Do not set a global Rust default just
for this repository: CI pins the toolchain per job and the schema suite
pins its own override.

## Generate for validation (committed output plus temporary check)

```sh
buf format --diff
buf lint
buf build
python3 scripts/validate-schema.py
```

`proto/syntra/v1` is the sole source of truth, with `proto/` as the v2 module
root. The old schema tree is removed. Historical declarations are read from
the archived `compatibility/v1-initial/historical.json` descriptor, not a
second source root or a Git checkout. Never combine historical and current
descriptor sets in one pool: fully qualified types and a logical file path collide.
`session.proto` and `capabilities.proto` intentionally define no messages;
some generators produce descriptor-only output or no corresponding source
file. Their existence does not mean those extensions are implemented.

Generation is committed: `buf generate --template buf.gen.yaml` writes
Rust output into `crates/syntra-core/src/generated/` and Go output into
`bindings/go/gen/`, both tracked and drift-checked (see
`docs/schema-registry.md` §11). Validation also regenerates into the
ignored `.tmp/` directory (see `.gitignore`) for reproducibility and
drift comparison. Consumers obtain language bindings from crates.io, the
Go module proxy, the committed tree, or GitHub Release assets — never a
registry. The validator writes a throwaway Go module and a throwaway
generation template into `.tmp/`; both are deleted on the next run and
are never tracked. Do not hand-edit committed generated code. No server,
client transport, HTTP status mapping, gRPC service, authentication
validator, or cryptographic implementation is generated.

## Complete validation

```sh
python3 scripts/validate-schema.py
```

This executes the four requested Buf commands, generates twice into
`.tmp/` and hashes all outputs to check repeatability, verifies the
initial FILE baseline, verifies the archived historical descriptor hash
and historical declarations, compares WIRE compatibility, asserts the
known historical FILE/source break remains visible, and compiles/tests
both language bindings from the temporary output. The manifest's
`historical_sources` path/hash provenance and `historical_image_sha256`
verify the immutable historical image generated from actual unchanged
sources at commit `92e5f281aa7c3adac9ba78588c1140b12d55c1d9` before removal.
The renumbering-negative test mutates only a temporary copy of the current
image: it is not a fake previous version. Baselines are never regenerated
by validation. Commands fail on errors and subprocesses have finite waits.
The updated Python suite has 13 checks (the original 12 plus a sole-source
regression check); post-deletion results remain pending in
[validation](validation.md). The original run there is historical evidence,
not a result for the updated suite.

Standalone language commands, after generation into `.tmp/` by
`scripts/validate-schema.py` (isolated schema suite on Rust 1.85.1;
workspace crates test separately on Rust 1.88):

```sh
go -C .tmp/bufgen/go build ./...
go -C tests/schema/go test -mod=readonly -count=1 -v ./...
cargo +1.85.1 test --locked --manifest-path tests/schema/rust/Cargo.toml
```

The explicit Rust toolchain is needed from the root: rustup locates overrides
by working directory, not by `--manifest-path`. From `tests/schema/rust`,
plain `cargo test --locked` uses the local override. The Python runner already
sets the right directory. Lockfiles/checksums are checked in; ordinary tests
do not run `go mod tidy` on the checked-in test module (the throwaway module
is tidied once, inside `.tmp/`, on each validation run). First-time dependency
downloads need the public Go/crates.io registries.

## What these tests establish

- Eight message declarations and one enum retain their historical fields,
  types, numbers, presence, oneofs, reservations, and values exactly.
- Shared independent hexadecimal fixtures for all six body variants and
  both result outcomes decode identically under both descriptor layouts;
  Go and Rust decode/round-trip those same fixtures.
- Empty success differs from unset outcome; arbitrary/non-UTF-8 payloads,
  full-width IDs and unknown enum numbers survive; field order is irrelevant.
- Malformed varints, truncated messages, illegal wire type, invalid UTF-8
  fail codec parsing. Missing outcomes, code zero, reserved tags, and
  multiple raw oneof alternatives demonstrate **codec limitations**, not
  an implemented protocol validator. Go preserves unknown fields; Prost
  drops them. Neither behavior adds application interpretation.

No live socket/transport interoperability, TLS validation, authentication,
authorization, allocation/rate limits, deadline/cancellation scheduling,
replay protection, or session conformance is implemented or tested here.
See [security test plan](../security/test-plan.md) for that separate work.

## Upstream references

- [Buf v2 generation configuration](https://buf.build/docs/configuration/v2/buf-gen-yaml/)
- [Prost plugin](https://github.com/neoeinstein/protoc-gen-prost/tree/protoc-gen-prost-v0.4.0)
- [Go generator](https://github.com/protocolbuffers/go/tree/v1.36.6)
- [Protobuf field presence](https://protobuf.dev/programming-guides/field_presence/)

The tested Prost v0.4.0 plugin does not accept the newer `flat_output_dir`
option shown in upstream main-branch docs; no such option is used.
