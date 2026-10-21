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

**Native Go integration (`-tags syntranative`) is unsupported.** Installing
a Release-built `libsyntra_ffi` does not enable it. The adapter in `native.go`
declares a proposed ABI that the current Rust crate does not export; linking
fails before its ABI version check can run. See [Native ABI blockers](#native-abi-blockers).

## Layout

| Path | Contents |
|---|---|
| `gen/syntra/v1/*.pb.go` | Generated types. Committed, drift-checked (see `.gitignore`). Regenerate, never hand-edit. |
| `syntra.go` | Package doc, type aliases, bounds, `RpcError` + normalization/branch helpers, frame/handshake/RPC validators, protowire codec pre-scan, handshake machine, correlation tracker. No messenger semantics. |
| `session.go` | `Transport` + `LoopbackPair`, `Client` (handshake pump, `Call` with context deadlines/cancellation, notifications, deterministic close), `Host` (`Serve` dispatch, `NotifyAll`), `HandlerFunc`, `StaticPolicy`. |
| `native.go` (`-tags syntranative`) | Unsupported CGO adapter proposal; incompatible with the current Rust FFI. |
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

## Native ABI blockers

`native.go` and [`crates/syntra-ffi/src/lib.rs`](../../crates/syntra-ffi/src/lib.rs)
describe different interfaces:

- Go expects `syntra_ffi_*` client/host frame operations with pointer handles.
  Rust exports `syntra_*` runtime/loopback operations with integer `u64`
  handles, including `syntra_open` and `syntra_handshake`.
- Go expects ABI integer `1`; Rust returns packed `1.0.0` (`0x10000`) from
  `syntra_abi_version` and provides `syntra_abi_compatible`. Rust buffers
  come from boxed slices and must use `syntra_free`; they do not implement
  the adapter's proposed malloc-compatible ownership contract. Rust method
  strings use NUL termination rather than Go's proposed explicit lengths.
- **Status mapping deferred:** Go's proposed table assigns -1 to invalid
  argument, -2 closed, -3 ABI mismatch, -4 memory, -5 expired, -6 internal.
  Rust actually defines -1 panic, -2 argument, -3 handshake, -4 RPC,
  -5 timeout, -6 cancelled, -7 unavailable, -8 resource, -9 version,
  -10 UTF-8, and +1 poll-again. Copying this table alone cannot repair the
  ABI or its different per-RPC error model. Restore a shared authoritative
  ABI/header first, then map and test every real status against that library.
- **Host default timeout deferred:** the proposed `syntra_ffi_host_open`
  drops resolved `HostConfig.DefaultTimeout` because it has no timeout
  parameter. The actual Rust `syntra_open` creates a loopback pair using
  `ConnectionConfig::default()` (30 seconds) and exposes no host-config
  entry point. A local extra C argument or Go-only timer would not configure
  the Rust deadline owner. ABI restoration must provide configuration to
  that owner and verify `timeout_ms=0` with a nondefault host budget. The
  supported pure-Go host already applies its resolved timeout (3 seconds
  by default; maximum configured/requested budget 30 seconds).

CGO typechecking/vetting of local declarations is not native integration
coverage. Native support requires real-library linking and lifecycle,
status, ownership, and deadline tests after these contracts are reconciled.
