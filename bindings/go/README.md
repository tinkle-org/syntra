# Syntra Go bindings

Go servers speak Syntra v1 through this module: generated Protobuf types
plus a transport-agnostic client/host session layer built on the
validation, codec, handshake, and correlation rules in
`specifications/core/` and `proto/syntra/v1/`.

## Installing

```sh
go get github.com/tinklehq/syntra/bindings/go
```

`go get` installs **the Go sources in this module only**. The supported
default build is pure Go and requires neither CGO nor a native library.
This module never downloads binaries. In this build, `NativeAvailable()`
returns false and `CheckABI()` returns nil because no native library is linked.

**Native Go integration (`-tags syntranative`) uses the production Rust core.**
Build the native library with `cargo build -p syntra-ffi --features production`,
then build Go with `-tags syntranative` against that library. The adapter in
`native.go` matches `crates/syntra-ffi/include/syntra_production.h`.
See [Native ABI](#native-abi).

## Layout

| Path | Contents |
|---|---|
| `gen/syntra/v1/*.pb.go` | Generated types. Committed, drift-checked (see `.gitignore`). Regenerate, never hand-edit. |
| `syntra.go` | Package doc, type aliases, bounds, `RpcError` + normalization/branch helpers, frame/handshake/RPC validators, protowire codec pre-scan, handshake machine, correlation tracker. No messenger semantics. |
| `session.go` | `Transport` + `LoopbackPair`, `Client` (handshake pump, `Call` with context deadlines/cancellation, notifications, deterministic close), `Host` (`Serve` dispatch, `NotifyAll`), `HandlerFunc`, `StaticPolicy`. |
| `native.go` (`-tags syntranative`) | Production CGO adapter matching `crates/syntra-ffi/include/syntra_production.h`. |
| `native_purego.go` (default) | Supported pure-Go client/host cores. |
| `wire_test.go` | Golden vectors from `conformance/test-vectors/protobuf/vectors.yaml` plus duplicate-body, reserved-field, truncation, and enum-normalization cases. |
| `session_test.go` | Lifecycle tests over loopback with neutral echo fixtures (`/example.Echo/Echo`, `/example.KV/Get`, `/example.Slow/Wait`). |

## Regenerating

Pinned toolchain (per `specifications/schema/generation.md`): Buf 1.59.0,
remote plugin `buf.build/protocolbuffers/go:v1.36.6` revision 1,
`paths=source_relative`, runtime `google.golang.org/protobuf v1.36.6`,
`go` floor `1.22`. Generate via Buf so headers stay drift-clean
(`protoc (unknown)`); local `protoc` builds stamp a different version
string and fail `validate-schema.py --drift-only`.

```sh
buf generate --template buf.gen.yaml
```

`buf.gen.yaml` writes Go output into `bindings/go`; do not run it with
`clean: true` on branches that do not own `bindings/go`. CI drift check:
`python3 scripts/validate-schema.py --drift-only`.

`session.proto` and `capabilities.proto` intentionally define no messages;
their generated files are descriptor-only.

## Checking

```sh
gofmt -l .            # must be empty
go vet ./...
go test ./...         # pure-Go core; needs no native library
go test -race ./...
```

## Scope notes

- Identity verification stays host-owned: `CredentialPolicy` receives
  opaque bytes and returns an opaque principal string. No messenger
  identity shapes, no gRPC clients, no token plumbing live here.
  Per-method authorization is host-owned via the optional
  `HostConfig.Authorize` hook (bound principal + method, before handler
  effects). Nil preserves the legacy allow-everything behavior for
  backward compatibility and diverges from the Rust `Handler::authorize`
  fail-closed default until set explicitly (`DenyAllAuthorize` for
  parity, `AllowAllAuthorize` for an explicit allow).
- Transports (TCP length-prefix, WebSocket binary, TLS, close codes)
  plug in through `Transport`; each `Send`/`Recv` carries exactly one
  serialized `Frame`.
- Excluded on purpose: Centrifuge/JSON gateways, Tinkle subscriptions,
  presence, and any service registry. Tests use neutral fixtures only.

## Resource and compatibility policy

- The serialized frame limit is 1 MiB, including envelope overhead. A
  payload at the separate 1 MiB payload limit may therefore fail encoding.
  Failed request encoding does not reserve a call slot or start its timer.
- Per connection, the pure-Go host admits notifications only while its
  shared outbound backlog has fewer than 256 frames. At saturation the
  core rejects the newest notification with `RESOURCE_EXHAUSTED`; terminal
  RPC errors and expiry results remain admissible. Draining restores
  notification admission. Each queued frame is also limited to 1 MiB.
  `Host.NotifyAll` is currently best-effort: it ignores per-connection core
  errors, so a nil broadcast return is not proof of enqueue or delivery.
- Unknown fields alongside a known body are tolerated. A frame with no
  known body but unknown top-level content returns `UNIMPLEMENTED`, matching
  the Rust core; a genuinely empty body returns `INVALID_ARGUMENT`.
  Only body tags 10–15 and reserved tags 16–17 are allocated. There is no
  specified future-body tag range. Distinguishing a mixed known/unknown
  body from metadata remains blocked by
  [RFC B5](../../rfcs/0001-public-idl-layout.md#b5-unknown-body-versus-metadata-discriminator).

## Native ABI

`native.go` matches [`crates/syntra-ffi/include/syntra_production.h`](../../crates/syntra-ffi/include/syntra_production.h)
and the `production` feature in [`crates/syntra-ffi`](../../crates/syntra-ffi/src/lib.rs):

- Pointer handles for initiator/responder cores, opened and closed exactly once.
- ABI version `1` on both sides via `syntra_ffi_abi_version` / `CheckABI`.
- Status table `0, -1..-6` for FFI-layer failures; per-RPC failures travel
  inside `RpcResult` frames.
- Owned outputs released with `syntra_ffi_free`; strings as `(ptr, len)`.
- Host authentication completes in the application: `host_accept_hello`
  validates and selects a version, then `host_auth_complete` binds the
  resolved principal and returns `ServerReady`.

The separate `syntra_*` loopback ABI remains test-only behind
`test-fixture` and `include/syntra.h`.

CGO typechecking alone is not integration coverage. Native verification
requires real-library linking plus lifecycle, status, ownership, deadline,
and concurrency tests.
