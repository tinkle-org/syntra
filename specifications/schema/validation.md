# Schema validation record — 2026-10-19

Scope: historical candidate-IDL and schema codec tooling runs, before and after
removal of the old schema tree. This is not a stable release,
RFC approval, runtime conformance result, or live transport interop report.

> The original results below are preserved as historical evidence. Subsequent
> archived-descriptor/sole-source checks were also executed; their results are
> recorded in the post-deletion section below (2026-10-19).

## Executed environment

macOS arm64; Buf 1.59.0; Go 1.26.4; Python 3.14.7; Rust/Cargo 1.85.1.
Rust was installed in an isolated temporary rustup home; no host-wide
default toolchain change was required. Remote plugins are pinned in
`buf.gen.yaml`; dependencies/checksums are in the Go and Rust lockfiles.

## Original commands and results (historical)

The full runner was executed with the isolated Rust environment:

```sh
python3 scripts/validate-schema.py
```

| Check executed by runner | Result |
|---|---|
| `buf format --diff --exit-code` | Pass, no diff |
| `buf lint` | Pass, STANDARD, no ignored rules/files |
| `buf build` | Pass, seven input schemas |
| `buf generate`, twice | Pass, Rust and Go emitted; eight output-file hashes identical |
| Python descriptor/tooling tests | 12 passed |
| Historical declaration comparison | All eight messages and one enum unchanged, including reservations/presence |
| Historical Buf WIRE audit | Pass |
| Historical Buf FILE audit | **Expected failure detected**; source migration was blocked at this run |
| Initial `v1-initial` FILE baseline | Pass; snapshot hash verified |
| Candidate-renumbering negative fixture | Accidental renumbering detected against the real initial snapshot |
| Historical/new shared fixture decoding | Seven fixtures give equal logical values under both descriptor layouts |
| Generated Go module compilation | Pass |
| Go codec tests | Four top-level tests passed, including seven fixture subtests |
| Rust codec tests, `cargo test --locked` | Four passed; zero doctests |

Also executed: `gofmt` validation, Rust `cargo fmt -- --check`, and
`git diff --check`. Historical `schema/` files had no diff at that time. A focused
static review found no additional security defect in this schema/tooling
scope; that is not an audit of a runtime implementation.

The historical FILE failures are:

- Deleted owning file `syntra/v1/error.proto` (types now in `errors.proto`).
- `Cancel`, `ClientHello`, `Frame`, `Notification`, `RpcRequest`, `RpcResult`,
  and `ServerReady` removed from historical `syntra/v1/session.proto`.

These failures were not hidden by changing `buf.yaml` or treated as proof
of source compatibility. Establishing the initial baseline (originally a candidate snapshot) did
not itself approve the migration. The subsequent user-directed layout
decision is recorded in [RFC B9](../../rfcs/0001-public-idl-layout.md#b9-recorded-layout-decision-and-known-source-break);
the FILE/source break remains a known breaking difference.

## Subsequent schema-tree deletion and archive validation (executed 2026-10-19)

Explicit user direction makes `proto/syntra/v1` the sole source of truth and
removes `schema/syntra/v1`. Before removal, an immutable
`compatibility/v1-initial/historical.json` FileDescriptorSet was generated from
the actual unchanged historical sources at commit
`92e5f281aa7c3adac9ba78588c1140b12d55c1d9` (verified hashes
`eed4f02e…` and `a877be50…` matching `manifest.json` before deletion).
The manifest retains `historical_sources` path/hash provenance and adds
`historical_image_sha256` (`c046e4f8…`); the existing `image.json` baseline
(`48b3206c…`) remains unchanged.

Updated tests read the archived descriptor hash and historical declarations
without a Git checkout or duplicate schema tree. The descriptor/tooling suite
has the original 12 checks plus a sole-source regression check (13 total).

Post-deletion executed results (isolated Rust 1.85.1, Buf 1.59.0, Go 1.26.4):

- `buf format --diff --exit-code`: pass, no diff
- `buf lint` (STANDARD, no exceptions): pass
- `buf build` (seven `proto/` schemas): pass
- `buf breaking --against compatibility/v1-initial/image.json`: pass
- `python3 -m unittest discover -s tests/schema -p test_schema.py`: 13 passed
- Historical WIRE audit against archived `historical.json`: pass
- Historical FILE break still detected (expected known difference): pass
- `buf generate` twice: 8 output files, byte-identical hashes
- Go codec tests: 4 passed (7 fixture subtests included)
- Rust codec tests (`cargo test --locked`): 4 passed
- `git diff --check`: pass; `git diff -- schema` shows only the two deletions

The layout decision does not establish formal maintainer quorum, behavioral
RFC acceptance, or resolution of the remaining protocol/security blockers.

## Corrections during verification

- Public-import forwarding files failed STANDARD's `IMPORT_NO_PUBLIC` rule;
  the final layout uses direct declaration ownership, without lint exceptions.
- Prost plugin v0.4.0 rejected the newer `flat_output_dir` option; removed.
- Runtime Prost 0.13.1 plus resolved derive 0.13.5 failed compilation. Runtime
  0.13.5 and its checked-in dependency lockfile compile and pass the tests.
- A FILE-negative test initially expected an individual `RpcError` deletion;
  Buf reports the deletion of its entire old file instead. The assertion now
  checks that real diagnostic and the moved `Frame` declaration.

## Remaining acceptance gaps

`session.proto` and `capabilities.proto` allocate no messages. Requested
new/renamed handshake, session, event, capability, operation-ID and error
contracts await normative decisions; the [A–G matrix](reference.md#delivered-versus-blocked-ag-coverage)
and [RFC blockers](../../rfcs/0001-public-idl-layout.md#10-unresolved-questions-and-blockers)
identify them individually. There was no accepted complete normative v1
behavioral suite to implement against at task start.

No protected-operation authorization, certificate/hostname verification,
credential expiry/revocation, byte/depth/allocation enforcement on network
input, queue/rate limits, deadlines/cancel races, session resumption, replay,
or live transports were implemented/tested. Unknown-body classification,
raw-oneof rejection and reserved-tag runtime rejection remain unresolved.
Those require a separate approved specification and implementation.
