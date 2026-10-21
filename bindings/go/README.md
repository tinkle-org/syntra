# Syntra Go bindings

Go servers speak Syntra v1 through this module: generated Protobuf types
plus a transport-agnostic client/host session layer built on the
validation, codec, handshake, and correlation rules in
`specifications/core/` and `proto/syntra/v1/`.

## Installing

```sh
go get github.com/tinklehq/syntra/bindings/go
```

`go get` installs **the Go sources in this module only**. The optional
native accelerator (`libsyntra_ffi`, built from `crates/syntra-ffi` and
shipped as a **GitHub Release** artifact) is a **separate prerequisite**:
this module never downloads binaries, and no Go code here fetches,
verifies, or executes remote artifacts.

- **Default build** (pure Go, no CGO, no native library): works out of the
  box for development, tests, and embedding.
- **Native build**: install one Release asset for your platform where the
  linker finds it (for example `/usr/local/lib`, or point `CGO_LDFLAGS` /
  `LD_LIBRARY_PATH` / `DYLD_LIBRARY_PATH` at it), then build with CGO and
  the tag:

```sh
go build -tags syntranative ./...
```

`NativeAvailable()` reports which core is linked; `CheckABI()` fails
closed when the linked library's `syntra_ffi_abi_version` differs from
the binding's `NativeABIVersion` (currently 1).

## Layout

| Path | Contents |
|---|---|
| `gen/syntra/v1/*.pb.go` | Generated types. Committed, drift-checked (see `.gitignore`). Regenerate, never hand-edit. |
| `syntra.go` | Package doc, type aliases, bounds, `RpcError` + normalization/branch helpers, frame/handshake/RPC validators, protowire codec pre-scan, handshake machine, correlation tracker. No messenger semantics. |
| `session.go` | `Transport` + `LoopbackPair`, `Client` (handshake pump, `Call` with context deadlines/cancellation, notifications, deterministic close), `Host` (`Serve` dispatch, `NotifyAll`), `HandlerFunc`, `StaticPolicy`. |
| `native.go` (`-tags syntranative`) | CGO wrapper over the `crates/syntra-ffi` C ABI: version check, client/host handles, borrowed-in/owned-out buffer discipline, status mapping, exactly-once close. |
| `native_purego.go` (default) | Pure-Go cores implementing the same session contract. |
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
go vet -tags syntranative ./...   # CGO wrapper typechecks; linking needs libsyntra_ffi
```

## Scope notes

- Identity verification stays host-owned: `CredentialPolicy` receives
  opaque bytes and returns an opaque principal string. No messenger
  identity shapes, no gRPC clients, no token plumbing live here.
- Transports (TCP length-prefix, WebSocket binary, TLS, close codes)
  plug in through `Transport`; each `Send`/`Recv` carries exactly one
  serialized `Frame`.
- Excluded on purpose: Centrifuge/JSON gateways, Tinkle subscriptions,
  presence, and any service registry. Tests use neutral fixtures only.

## Known gaps

- `native.go` (`-tags syntranative`) currently declares a proposed
  `syntra_ffi_*` client/host frame API. The landed `crates/syntra-ffi`
  exports `syntra_abi_version` / `syntra_abi_compatible` plus a loopback
  runtime facade with different entry points. The CGO wrapper typechecks
  and vets clean, but linking against the current Release-built library
  will fail until the FFI header contract is reconciled. Default builds
  use the pure-Go core and are unaffected.
