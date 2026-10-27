# Production runtime and recovery boundary

This document describes the supported production embedding path and the
application-owned recovery contract.

## One Rust engine

The production protocol engine is Rust:

- `syntra-core` owns envelope codec, validation, version negotiation,
  correlation, and typed errors.
- `syntra-runtime` provides async initiator/host engines with
  connection-bound sessions, deadlines, cancellation, and bounded queues.
- `syntra-ffi` with the `production` feature implements a separate C
  frame-pump with the same protocol mechanics (version negotiation, frame
  validation, correlation, deadlines, cancellation observation, outbound
  queueing) on top of `syntra-core`, exposed through
  `include/syntra_production.h`. It does not wrap
  `syntra-runtime::Initiator`/`Host`; the embedding application owns the
  transport pump (see `crates/syntra-ffi/src/production.rs` module docs).
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

## SC1 design boundary (not runtime support)

The embedding paths and native ABI in this guide describe the current
runtime. [Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md)
selects transport-independent SC1 but is not Accepted and adds no Rust,
Go, or FFI crypto/binding support. Baseline TLS requirements and existing
executable conformance profiles remain unchanged.

In the proposed [SC1 design](../specifications/security/secure-channel.md),
carrier I/O stays outside the core; one channel state machine serves
[TCP/UDP/WS bindings](../specifications/transports/noise-bindings.md).
The core does not dial sockets or require WS or gRPC. Existing HTTPS/WSS
TLS compatibility remains, with outer TLS still required for browser
`wss://`. Noise-in-WS is a distinct wire binding from current WS/WSS
profile IDs and their serialized-`Frame` mapping; existing frame-pump
calls are not Noise-record APIs.

Host policy would still own [enrollment, AK storage, authorization, and
revocation](../specifications/security/device-authorization.md), without
mandatory human accounts. Selected NK enrollment and NKpsk0 returning
channels use empty M1/M2 payloads, a unique random shared 32-byte AK plus
opaque 8-byte `auth_id` per device, and fresh ephemeral material/directional
traffic keys per channel. The AK is not sent on reconnect or carried as
`connection_id`. Verification of the first authenticated client transport
record precedes protected actions, and Syntra hello/ready still applies.

Returning-device authentication adds no session resumption or automatic
RPC retry to the recovery contract below. The
[SC1 conformance plan](../conformance/plans/secure-channel.md) is future
verification; native linking or existing runtime tests do not prove SC1.

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

Go (from `bindings/go`, per `.github/workflows/repo-validation.yml`):

```sh
CGO_LDFLAGS="-L../../target/debug -lsyntra_ffi" LD_LIBRARY_PATH="../../target/debug" go test -tags syntranative -count=1 ./...
```

CI builds the library with `cargo build --locked -p syntra-ffi
--features production` and uses `LIBDIR="$GITHUB_WORKSPACE/target/debug"`
(`CGO_LDFLAGS="-L$LIBDIR -lsyntra_ffi"`,
`LD_LIBRARY_PATH="$LIBDIR:$LD_LIBRARY_PATH"`). `-tags syntranative`
alone does not link the library.

## Recovery

`syntra-runtime` reports transport acceptance, completed outcomes, expiry,
cancellation, capacity exhaustion, and transport loss (as `UNAVAILABLE` to
in-flight waiters). The native ABI does not: `syntra_ffi_client_close`
silently clears pending RPCs and no production FFI call reports transport
loss, so native embedders must surface transport loss to in-flight calls
themselves (fail each waiter as `UNAVAILABLE` with unknown outcome, never
as success or proof of non-execution). Applications report stream continuity loss to the
recovery coordinator (`RecoveryInput::ContinuityLost` / `GapDetected` in
`syntra-runtime::recovery`); the core never synthesizes stream positions.
It does not decide application recovery.

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
