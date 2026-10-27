# Schema generation and validation

Status: development tooling; not a protocol conformance claim. See
[reference](reference.md), [compatibility](compatibility.md), and
[RFC 0001](../../rfcs/0001-public-idl-layout.md) for the recorded layout
decision and remaining behavioral blockers.

## Pinned generators and toolchains

| Component | Pin | Role |
|---|---|---|
| Buf CLI | **1.59.0** | v2 module/compiler, STANDARD lint and FILE gate |
| Python tested | **3.14** | Validator tooling (`pyyaml`); see workflow `setup-python` pins |

Versions are deliberate pins, not claims to be latest. Schema validation in
this repository is Buf-only: format, lint, build, and breaking checks. This
repository commits and generates no language bindings.

Downstream language projects generate their own types with the following
recorded pins (documented recipe, not executed here):

| Component | Pin | Role |
|---|---|---|
| Rust generator | `buf.build/community/neoeinstein-prost:v0.4.0`, **revision 1** | Message/enum types, no networking or gRPC |
| Go generator | `buf.build/protocolbuffers/go:v1.36.6`, **revision 1** | Message/enum types, `paths=source_relative` |
| Rust runtime | `prost = "=0.13.5"` | Runtime/derive alignment |
| Go runtime | `google.golang.org/protobuf v1.36.6` | Bindings runtime |
| Go language floor | **1.22** | `go.mod` floor (1.26.4 tested downstream) |

Remote generation (downstream) uses BSR-hosted plugins for byte-identical
output only; it never pushes schemas and requires no registry identity
(`buf.yaml` has no `name:`). It needs HTTPS access to those public
generators, not locally installed generator binaries. Schema descriptors,
including comments, are submitted to those public generators: use only
public schema sources, never production payloads or credentials. No
floating `latest`, private plugin, or unpinned fallback is documented.
Generator availability/trust remains a downstream dependency; pins do not
make remote generation an offline build or attest the service's execution
environment.

Buf supplies the schema compiler. There is **no external `protoc` import
or binary dependency** in this workflow; the installed `protoc 35.1` was
not used. There are no external `.proto` imports, so no `buf.lock` dependency
lockfile is required. Schema imports are all `syntra/v1/*.proto`.

Install the exact Buf CLI release using the official
[installation guide](https://buf.build/docs/cli/installation/), and check
`buf --version` prints `1.59.0`. Python 3.14 runs the validator tooling.
No Rust or Go toolchain is needed in this repository: language generation
and implementation tests are downstream-owned (see the recorded pins
above).

## Generate for validation

```sh
buf format --diff --exit-code
buf lint
buf build
buf breaking --against 'compatibility/v1-initial/image.json'
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

This repository does not generate language bindings. Downstream language
projects regenerate their own committed types with the recorded pins and
drift-check that output in their own CI. Do not hand-edit generated code
anywhere. No server, client transport, HTTP status mapping, gRPC service,
authentication validator, or cryptographic implementation is generated.

### RFC 0007 boundary (informative)

[Draft RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
adds no `.proto` fields or generation step. Regenerating these message types
does not implement the proposed [Noise channel](../security/secure-channel.md),
[shared-AK enrollment/lifecycle](../security/device-authorization.md), or
[carrier record mappings](../transports/noise-bindings.md). The selected
NK/NKpsk0 suites require separate channel code, trusted host authentication
context and reviewed bindings; no generator supplies those contracts.
`ClientHello.credential` stays opaque and `ServerReady.connection_id` stays
diagnostic, with no AK/handle issuance field. Current generator pins, output
paths, compatibility gates and codec fixtures keep their existing meaning;
the [planned channel acceptance cases](../../conformance/plans/secure-channel.md)
are separate from schema-generation evidence.

## Complete validation

```sh
python3 scripts/validate-schema.py
```

This executes the Buf format, lint, build, and breaking checks against
the initial FILE baseline, then runs the Python schema suite. The suite
verifies the archived historical descriptor hash and historical
declarations, compares WIRE compatibility, and asserts the
known historical FILE/source break remains visible. The manifest's
`historical_sources` path/hash provenance and `historical_image_sha256`
verify the immutable historical image generated from actual unchanged
sources at commit `92e5f281aa7c3adac9ba78588c1140b12d55c1d9` before removal.
The renumbering-negative test mutates only a temporary copy of the current
image: it is not a fake previous version. Baselines are never regenerated
by validation. Commands fail on errors and subprocesses have finite waits.
The Python suite has 13 checks (the original 12 plus a sole-source
regression check); post-removal results remain pending in
[validation](validation.md). The original run there is historical evidence,
not a result for the updated suite.

## What these tests establish

- Thirty-one message declarations and one enum retain their historical
  fields, types, numbers, presence, oneofs, reservations, and values
  exactly (the eight original messages plus the RFC 0006 draft recovery
  profile declarations).
- Shared independent hexadecimal fixtures for all six body variants and
  both result outcomes decode identically under both descriptor layouts;
  language codec suites verify the same fixtures in their own
  repositories.
- Empty success differs from unset outcome; arbitrary/non-UTF-8 payloads,
  full-width IDs and unknown enum numbers survive; field order is irrelevant.
- Malformed varints, truncated messages, illegal wire type, invalid UTF-8
  fail codec parsing. Missing outcomes, code zero, reserved tags, and
  multiple raw oneof alternatives demonstrate **codec limitations**, not
  an implemented protocol validator. Codec unknown-field policies differ
  per generator and add no application interpretation.

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
