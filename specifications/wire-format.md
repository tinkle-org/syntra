# Syntra 1.0 — Wire format

Syntra envelopes use Protocol Buffers with bounded decoding and explicit
raw-field validation. The [IDL](../proto/syntra/v1/) defines field numbers,
types, and reservations; this page defines validation and compatibility.
BCP 14 keywords apply.

Carrier framing belongs to [transports](transports.md), protection to
[security](security.md), readiness to [connection](connection.md), and
correlation and error meanings to [RPC](rpc.md).

## General model

The initiator opens a connection, presents opaque credentials, invokes
methods, and receives correlated results and uncorrelated notifications.
The host validates identity/version/state and dispatches authorized work.
A principal may identify a device, service, key, or application-defined
entity; no human-account model is required. A default logical session is
exactly one connection lifetime; durable application progress is separate.

**SNTR-CORE-001**, **SNTR-CORE-002** — The core MUST remain application-neutral
and treat credentials, method names beyond syntax, application payloads,
notifications, and principal handles as opaque. It MUST NOT add application
business types or parse/decrypt application ciphertext.

**SNTR-CORE-004** — Mandatory interoperability comprises handshake,
authentication interface, RPC, cancel, typed errors, and version negotiation.
Optional behavior uses its post-ACTIVE capability RPC; there is no
generic capability enumeration, hello extension list, or optional-frame probe.

**SNTR-CORE-005** — Transport receipt or protection success MUST NOT be
reported as application processing; only a correlated application result
establishes the outcome described by that result.

**SNTR-CORE-006** — Public production MUST use a production-permitted
protected carrier under [transports](transports.md); restricted carriers
remain development-only.

**SNTR-CORE-010**, **SNTR-CORE-011**, **SNTR-CORE-012** — The initiator MUST
send exactly one first-envelope hello, await ready before application
requests/cancels/payloads, correlate results by request ID, and handle
interleaved notifications without treating them as completion. Carrier
setup pipelining never permits pre-ACTIVE RPCs.

**SNTR-CORE-020**, **SNTR-CORE-021**, **SNTR-CORE-022** — The host MUST
validate versions and credentials, select exactly ready or terminal
handshake failure, and MUST NOT dispatch handlers or emit notifications
before ACTIVE or authorize protected effects before authentication. It
MUST enforce frame/concurrency/handshake bounds with their typed failures.
The state machine and local-cause/native-signal split belong to [connection](connection.md).

**SNTR-CORE-030**, **SNTR-CORE-031** — Violations MUST be rejected with
the appropriate shape/state cause in lawful RPC context or local cause
plus native closure otherwise. No invented pre-ACTIVE error frame is
permitted. Failures MUST be deterministic and bounded: no panic, unbounded
allocation, or silent future-body drop.

**SYN-ARCH-011**, **SYN-ARCH-013** — Carrier processing MUST NOT parse,
decrypt, or semantically validate opaque application payloads or credentials
beyond their defined carriage. Syntra MUST carry opaque application bytes
without parsing or decrypting application ciphertext. Application encryption
and decryption occur above Syntra.

**SYN-ARCH-012** — Protobuf encoding MUST remain separate from carrier
framing. A carrier change does not change `Frame` representation; schema
evolution does not implicitly redefine carrier framing.

**SYN-ARCH-020**, **SYN-ARCH-021** — Implementations MUST preserve schema
reservations, tolerate bounded unknown metadata, and reject future body
variants with `UNIMPLEMENTED` under §2's raw-wire precedence, never silently
drop them. No compatibility exception bypasses that validation.

**SYN-ARCH-030** — Public production MUST use a permitted protected
carrier: encrypted TCP or verified WSS under [transports](transports.md).
WS is explicitly enabled loopback development only. HTTP/HTTPS
request-response and UDP have no Syntra 1.0 binding.

**SYN-ARCH-031** — Implementations MUST use established cryptographic
and TLS implementations and MUST NOT invent algorithms, ratchets, or
custom ciphers. The selected protection contract is owned by [security](security.md).

**SYN-ARCH-032**, **SYN-ARCH-033** — Credentials MUST remain opaque
sensitive bytes: no core logging, persistence, interpretation, or unsafe
production carriage. Hosts MUST NOT grant protected access before
authentication. Failures use `UNAUTHENTICATED`/`PERMISSION_DENIED` under
the connection/RPC rules, without credentials or private diagnostics.

**SYN-ARCH-034**, **SYN-ARCH-035** — Implementations MUST bound buffers,
frames, concurrency, call budgets, and handshakes, with deterministic
timeout/cancellation and no panic or unbounded allocation on untrusted
input. Transport/framing/protection success MUST NOT be reported as
application processing; only a success `RpcResult` proves application success.

## 1. Envelope and opaque bytes

Every message has a version, a request identifier, and one body. The
[envelope schema](../proto/syntra/v1/envelope.proto) defines their encoding:

| Field | Type | Meaning |
|---|---|---|
| `version` | `uint32` | Offered maximum in hello; selected version afterward |
| `request_id` | `uint64` | Connection-scoped correlation; zero for handshake and notifications |
| `body` | `oneof` | Exactly one of the bodies below |

| Body | Direction | Contents |
|---|---|---|
| `hello` | Client → server | Version range and opaque credential |
| `ready` | Server → client | Connection identifier; version selection is in the envelope |
| `request` | Client → server | Method, opaque payload, and timeout budget |
| `result` | Server → client | Opaque success payload or typed error |
| `cancel` | Client → server | No body fields; targets the envelope's request identifier |
| `notification` | Server → client | Opaque notification payload |

The byte stream inside authenticated records is `u32BE(length)` followed by
the serialized envelope. This length is distinct from transport framing;
[transports](transports.md) defines how records carry the stream.

**SNTR-SER-001** — Syntra MUST use proto3 binary encoding for all core
messages. `proto/syntra/v1/` is the sole authority for field numbers,
types, and reserved values; prose MUST NOT redefine them.

**SNTR-WIRE-001** — Every Syntra envelope MUST be exactly one serialized
`Frame`. Implementations MUST NOT send bare requests, results, or
notifications, or batch multiple frames inside one Protobuf message.
Carrier segmentation and concatenation are governed by [transports](transports.md).

**SNTR-WIRE-002** — The defined bodies are `hello`, `ready`, `request`,
`result`, `cancel`, and `notification`. Producers MUST set exactly one.
An empty body or more than one raw body occurrence, including a repeated
same alternative, MUST be rejected before generated merge semantics.

**SNTR-WIRE-003** — Invalid combinations MUST be rejected before effects:

| Body | `request_id` | Legal phase |
|---|---|---|
| `hello`, `ready` | 0 | Their handshake states only |
| `notification` | 0 | Emit only in ACTIVE; receive in ACTIVE or as in-transit input during CLOSING |
| `request`, `cancel` | Nonzero | ACTIVE only |
| `result` | Nonzero | Lawful RPC context after readiness |

A result also requires exactly one outcome (`payload` or `error`).
Pre-ACTIVE notifications fail-close without delivery or later queueing.
During CLOSING, an already in-transit valid notification follows the
[connection receive rule](connection.md#1-establishment-and-states):
admit to the bounded notification queue if possible, otherwise account
loss. It never completes an RPC or authorizes new host emission.

**SNTR-WIRE-006** — The frame ceiling of **1,048,576 bytes** (1 MiB)
measures the complete serialized `Frame`, including opaque payload,
unknown fields, tags, lengths, version, correlation, method, and budget.
Exactly MAX is within the bound; MAX+1 MUST be rejected before dispatch.
A 1 MiB payload alone does not fit. Another bound requires an explicitly
negotiated capability bound or explicit carrier bound rule; deployments MUST
document their bounds and MUST NOT silently raise them for large payloads
or insecure/offline operation. Oversize yields `RESOURCE_EXHAUSTED` where
a lawful RPC context exists, otherwise closure.

**SNTR-WIRE-007** — Empty request payload invokes empty input; selected
empty result payload means success with empty output; empty notification
payload is valid. Presence is determined by field/oneof presence, never
by byte length. Unset result outcome is not success.

**SNTR-SER-002** — Protobuf serialization is NOT canonical. Multiple byte
sequences MAY represent the same logical message. Implementations MUST NOT
hash, sign, or compare serialized bytes for logical-message equality;
they MUST compare decoded fields. Opaque application bytes remain
bit-preserved; their application-defined meaning is outside the codec.

## 2. Bounded raw validation and first-error precedence

**SNTR-SER-003**, **SNTR-WIRE-004** — Validate the two discriminated
messages (`Frame.body` and `RpcResult.outcome`) before generated decoding
can erase multiplicity. Non-canonical ordering and non-minimal valid
varints within bounded widths remain accepted. The partition is:

| Message | Known fields | Forbidden | Future discriminator | Unknown metadata |
|---|---|---|---|---|
| `Frame` | Headers 1/2; bodies 10..15 | Top-level 16/17 | Bodies 18..31 | 3..9 and 32+ |
| `RpcResult` | Outcomes 1/2 | None | Outcomes 3..15 | 16+ |

For a complete bounded frame, the first failing step determines the error:

1. Validate all wire structure, lengths, varints, and nesting, including
   unknown fields. Malformed structure or a wrong wire type for **any
   occurrence** of a schema-known core field is `INVALID_ARGUMENT`.
   Validate known core message boundaries recursively, including repeated
   occurrences such as `RpcRequest.timeout_ms`; a later valid occurrence
   never hides an earlier wrong-type occurrence. Opaque payload and
   credential bytes are never parsed as core submessages. Capability payloads
   follow their own schema.
2. Reject any top-level `Frame` field 16/17 with `INVALID_ARGUMENT`,
   irrespective of other metadata.
3. Reject more than one occurrence in body space with `INVALID_ARGUMENT`,
   including known-plus-future and repeated same-body occurrences.
4. A sole structurally valid body in 18..31 is `UNIMPLEMENTED`; no body is
   `INVALID_ARGUMENT`. Known and future body alternatives are
   length-delimited; other wire types fail step 1.
5. After complete structural and raw-discriminator validation, enforce
   the field-specific byte ceilings on **every occurrence** of known
   `ClientHello.credential` (8,192 raw bytes), `ServerReady.connection_id`
   (128 UTF-8 encoded bytes), and `RpcError.message` (4,096 UTF-8 encoded
   bytes), before generated decoding or version/ID/state validation.
   Exactly the field maximum is within its ceiling. A credential above
   its ceiling yields `RESOURCE_EXHAUSTED`; a connection ID or diagnostic
   above its ceiling yields `INVALID_ARGUMENT`. An oversized occurrence
   MUST NOT be hidden by a later smaller occurrence or generated merging.
6. Only then decode the admitted known body and apply the remaining
   validation below before effects. Unknown metadata is ignored within
   the same byte/depth limits, regardless of order, and never affects
   mandatory interoperability.

`RpcResult.outcome` has the same raw-occurrence policy: more than one
outcome (even the same one twice) is `INVALID_ARGUMENT`, a sole structurally
valid future outcome in 3..15 is `UNIMPLEMENTED`, and no outcome is
`INVALID_ARGUMENT`. Empty selected success remains valid. These raw
discriminator checks also complete before step 5's field-limit checks.
Outside these two groups ordinary singular fields retain Protobuf
merge/last-value semantics **only among admitted occurrences**.
Rejections follow carrier/state rules; none permits a pre-ACTIVE error result.

For example, an otherwise structurally valid hello Frame with
`version=0` and an 8,193-byte credential fails `RESOURCE_EXHAUSTED` at
step 5 before its version error is considered, even if a later credential
occurrence is smaller. Before ACTIVE this is the detecting side's local
cause followed by native closure, not a wire error result. The complete
serialized-frame MAX/MAX+1 rule in §1 remains independently applicable.

**SNTR-SER-008**, **SNTR-WIRE-008** — `reserved 16, 17` and reserved names
`event`, `resume`, `ack` MUST be preserved and never emitted. Runtime
reject-on-occurrence applies to top-level `Frame` numbers 16/17 only.
Those numbers inside nested messages are unknown fields, tolerated within
bounds. Reserved names are schema reservations, not binary wire strings.

**SNTR-SER-008A** — Duplicate `version`/`request_id` scalars follow
Protobuf last-value semantics and MUST NOT be rejected merely for being
duplicates. Type-check each occurrence, admit it under the raw validation
and field-limit rules above, then validate the merged value.
`Cancel` has no defined inner fields: any well-formed inner bytes MUST be
tolerated; malformed inner wire still fails `INVALID_ARGUMENT`.

**SNTR-WIRE-005**, **SNTR-SER-005** — After the complete structural,
discriminator, and every-occurrence field-limit passes above, decode and
validate in order: negotiated version (or proposed range in
handshake), zero/nonzero ID discipline, variant-state legality, then
per-variant semantic checks. First failure determines the error; validation
MUST finish before dispatch. [RPC](rpc.md#2-request-identifiers-and-ordered-admission)
owns ordered high-water admission before method validation/authorization
and concurrency checks. [Connection](connection.md) owns handshake failures.

**SNTR-SER-006** — Implementations MUST enforce decoded message size no
larger than the envelope bound, embedded-message depth at most 32, and
total allocation bounded before full parse using a limited reader or
equivalent. Limit exhaustion yields `RESOURCE_EXHAUSTED` in lawful RPC
context or handshake/transport closure, never panic or OOM.

**SNTR-SER-007** — Truncated varints, illegal wire types, overlong lengths,
invalid UTF-8 in strings, and depth/size violations MUST be rejected
deterministically. Malformed input maps to `INVALID_ARGUMENT`, resource
limits to `RESOURCE_EXHAUSTED`, or closure where the state/carrier requires.
Implementations MUST NOT panic, allocate unboundedly, or leak private
state. Unknown-field skipping respects wire lengths; errors are generic
and never echo raw bytes, credentials, or private diagnostics.

## 3. Endpoint obligations

- **SNTR-SER-010** — Clients MUST use conformant proto3 encoders, emit only
  defined fields, never emit reserved values, and tolerate unknown fields.
- **SNTR-SER-011** — Clients MUST validate every received message before
  acting, including ready/results whose application payload they do not
  interpret (syntactic and bound checks only).
- **SNTR-SER-020** — Hosts MUST apply identical encode/validate rules and
  validate hello version ranges and credential lengths before authentication.
- **SNTR-SER-021** — Hosts MUST NOT interpret unknown fields as capabilities
  or authentication signals.
- **SNTR-WIRE-010** — Clients MUST stamp the negotiated version after
  handshake (proposed range before), enforce the receive bound before full
  parse, and use strictly increasing nonzero request IDs in emission order,
  never reusing allocated, skipped, or retired IDs. [RPC](rpc.md) owns the
  complete ID lifecycle.
- **SNTR-WIRE-011** — Clients MUST reject state/variant violations without
  application effects; an unknown/late result is ignored with a bounded
  diagnostic and MUST NOT fail the connection merely for being untracked.
- **SNTR-WIRE-020** — Hosts MUST apply identical validation and concurrency
  bounds and MUST NOT dispatch invalid envelopes.
- **SNTR-WIRE-021** — Hosts MUST stamp the selected version on every
  post-handshake envelope and MUST NOT change it mid-connection.

## 4. Version and compatibility

**SNTR-VER-001** — Version dimensions MUST NOT be conflated: the schema
package is `syntra.v1`, `Frame.version` is integer **1**, carrier revisions
identify their own bindings, and optional capability payload versions identify
their own payloads. The specification
label **Syntra 1.0** does not add a minor wire field.

**SNTR-VER-002**, **SNTR-VER-007**, **SNTR-VER-010** — The initiator MUST
offer its full nonzero ordered version range; the host selects the highest
overlap or fails with `UNIMPLEMENTED` and native close. Selected version
holds for the connection lifetime. Peers MUST NOT silently negotiate below
the highest mutual version; security downgrades MUST be refused. Clients
report rejection rather than silently retry weaker and record selected versions.

**SNTR-SER-004**, **SNTR-VER-004**, **SNTR-VER-011** — Optional
metadata MUST be accepted and ignored within the same limits and MUST NOT
be required without prior capability negotiation. Future-body rejection
follows §2, never silent success. Clients tolerate unknown error codes as
specified in [RPC](rpc.md#5-error-vocabulary).

**SNTR-VER-003**, **SNTR-VER-005** — Additive optional fields, capability-gated
variants, codes, transports, and extensions MUST remain backward compatible.
Repurposed fields, changed types, new required behavior, altered state
machines/failure semantics, weakened security, and reservation reuse are
breaking: they REQUIRE a new wire major. Reservations remain preserved
across all wire-version-1 revisions. Preserve published numbers, names,
types, package identity, presence, and oneof membership; reserve removed
field/enum numbers and names.

**SNTR-VER-020**, **SNTR-VER-021** — Hosts MUST publish supported versions,
carriers with security labels, and capabilities, select deterministically,
never accept an unimplemented version, and gate breaking changes behind a
new major. A mid-connection version change fails `FAILED_PRECONDITION`
and closes. Transport revisions do not
silently change core semantics. Negotiation is integrity-protected in
production; hosts prefer the highest secure overlap and log anomalies
without secrets.
