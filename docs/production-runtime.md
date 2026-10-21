# Production runtime and recovery boundary

This document describes the supported production embedding path and the
application-owned recovery contract.

## One Rust engine

The production protocol engine is Rust:

- `syntra-core` owns envelope codec, validation, version negotiation,
  correlation, and typed errors.
- `syntra-runtime` owns initiator/host state machines, connection-bound
  sessions, deadlines, cancellation, and bounded queues.
- `syntra-ffi` with the `production` feature exposes those cores through
  `include/syntra_production.h`.
- The Go module uses that ABI under `-tags syntranative`. The default
  pure-Go build remains available for development and comparison.

## Ownership

| Concern | Owner |
|---|---|
| Transport bytes, TLS, framing, pumps | Embedding application |
| Version negotiation, validation, correlation, deadlines, cancellation | Rust core |
| Credential verification, principal binding decision | Host application |
| Per-method authorization | Host application |
| Method dispatch and result construction | Host application |
| Payload schemas, persistence, replay retention, snapshots | Application |
| Stream checkpoints and recovery RPC selection | Application |

The core never parses application payloads and never performs network I/O.

## Native ABI

Authoritative header: `crates/syntra-ffi/include/syntra_production.h`.

- ABI version `1` via `syntra_ffi_abi_version`; Go verifies with `CheckABI`.
- Opaque `syntra_ffi_client_t` / `syntra_ffi_host_t` handles.
- Inputs are borrowed `(ptr, len)`; outputs are owned and freed once with
  `syntra_ffi_free`.
- Status codes report FFI-layer failures only. RPC outcomes travel inside
  `RpcResult` frames.
- Completion tokens in `syntra-runtime::policy` are distinct from wire
  `request_id` values so late and duplicate completions resolve explicitly.
- Host authentication is asynchronous in the application: validate hello,
  resolve policy, then complete with a principal to receive `ServerReady`.

Build:

```sh
cargo build -p syntra-ffi --features production
```

Go:

```sh
go test -tags syntranative ./...
```

## Recovery

The core reports transport acceptance, completed outcomes, expiry,
cancellation, capacity exhaustion, and continuity loss. It does not decide
application recovery.

Applications define streams and checkpoints:

- `stream`: independently ordered scope, opaque to the core.
- `generation`: continuity epoch; changes require an explicit decision.
- `base`: state required before applying a batch.
- `checkpoint`: state reached after the complete batch commits.

Rules:

1. Validate a complete batch before effects.
2. Persist effects and checkpoint atomically where possible.
3. Advance only after the owning application confirms persistence.
4. On gap, recover from the committed checkpoint; never skip forward.
5. On expired continuation, use the snapshot path.
6. Pair snapshots with a proven synchronization cut before resuming live.

`syntra-runtime::recovery` provides the generic `StreamRecovery`
coordinator and `RecoveryAction` values. It never invokes an RPC. The
application chooses replay, snapshot, and subscription methods.

## Distribution

Rust crates ship through `crates.io` with per-crate tags. The Go module
ships as source at `github.com/tinklehq/syntra/bindings/go` with paired
`bindings/go/vX.Y.Z` tags. Native libraries are built from the tagged
source with the `production` feature; the downloaded Go module documents
the required header and linking setup. Platform matrices and checksums are
published with releases.
