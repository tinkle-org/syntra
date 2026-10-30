# Syntra Secure Channel v1 — Shared channel

- Status: Accepted (2026-10-29) — RFC 0007; normative profile `SNTR-SC1-WSS-V1`
- Date: 2026-10-29
- Owner: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
- Scope: Channel establishment and record security, independent of carrier I/O
- Requirements: `SNTR-SC-001`–`SNTR-SC-015`; carrier requirements `SNTR-SCW-001`–`SNTR-SCW-012`

BCP 14 keywords below are normative for the accepted shared channel.
[transport-security.md](transport-security.md) and ADR-008 remain in force:
SC1/WSS runs inside verified TLS 1.3 and does not replace outer TLS. The
[device authorization](device-authorization.md) owner defines enrollment and
lifecycle; [noise-bindings.md](../transports/noise-bindings.md) defines the
accepted v1 byte mappings, first-envelope rule, Upgrade admission and direct
TLS topology. The registered profile and cases are in
[`conformance/profiles.yaml`](../../conformance/profiles.yaml) and
[`conformance/manifest/sc1-wss.yaml`](../../conformance/manifest/sc1-wss.yaml).
Registration is not an execution result. Independent vectors,
cross-implementation interoperability, mobile/recovery evidence and independent
security review remain release gates. HTTP/HTTPS request-response is excluded
from SC1, TCP/WS are restricted development carriers, and UDP remains deferred.

## 1. Channel construction

**SNTR-SC-001** — Both endpoints MUST use an established implementation of
`Noise_NK_25519_ChaChaPoly_SHA256` for bootstrap and
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` for enrolled-device channels. The
initiator MUST obtain the responder's trusted static public key through an
authenticated provisioning/rotation process. Neither peer may introduce a
custom cipher, key schedule, pattern variation or PSK-only reconnect path.
Server key trust is not learned from the unauthenticated peer.

**SNTR-SC-002** — Shared channel state MUST be independent of socket and
carrier libraries. Both roles consume/produce bounded channel messages;
carrier adapters own I/O, message delimiting and connection management. The
core MUST NOT acquire device-store, socket or carrier-specific dependencies
through this profile. Application ciphertext remains opaque above Syntra.

**SNTR-SC-003** — Both roles MUST authenticate identical versioned context
through the standard Noise prologue: selected bootstrap/returning mode,
carrier binding, server-key selector, intended endpoint scope and, for
returning devices, authorization handle and epoch. The AK MUST enter through
the Noise PSK input, never the prologue. The exact canonical encoding is defined
in [noise-bindings.md](../transports/noise-bindings.md) §2: ASCII
`syntra.sc1.v1`, mode `1`/`2`, carrier `1`/`2`/`3`, `u32BE server_key_id`,
`u64BE` epoch, eight opaque handle bytes, `u16BE` scope length and 1–255 bytes
of exact UTF-8 scope. The context is 38–292 bytes, prefixes M1 in clear and is
supplied unchanged as the Noise prologue. There is no padding, terminator or
additional domain. A local configuration mismatch MUST fail rather than invoke
another mode or a legacy format.

**SNTR-SC-004** — Both Noise handshake payloads MUST be empty. Both roles
MUST reject unexpected payload data and MUST NOT send credentials, enrollment
requests, RPCs or other application effects as early handshake data. A replay
of the first flight MUST NOT create an authorized Syntra binding or invoke
application handlers. Bounded transient handshake state is not authorization.

**SNTR-SC-005** — Each role MUST use fresh ephemeral key pairs for every
new handshake attempt, generated through the established implementation's
cryptographically secure randomness. Entropy failure MUST fail closed. Both
roles MUST discard obsolete ephemeral/handshake secrets promptly and MUST
NOT cache them for reconnect. Static server keys and persistent AKs have
separate lifecycle/storage rules.

## 2. Establishment and authentication ordering

**SNTR-SC-006** — The initiator MUST verify M2 before sending Syntra `hello`.
The responder MUST authenticate at least one client transport record under the
new keys before treating the client as freshly confirmed. The first
authenticated plaintext MUST begin with exactly one complete framed
`ClientHello` and no trailing envelope, as defined in
[noise-bindings.md](../transports/noise-bindings.md) §7; the hello envelope MAY
span records, and the record that completes it ends at the hello boundary. The
host MUST then validate the hello, evaluate the
enrollment's current principal/scope and same-principal binding, and apply
per-method authorization before `ready` and before protected effects. The
client MUST wait for `ready` before protected RPCs. PSK possession does not
bypass method authorization. For bootstrap, application credentials or an
explicitly authorized provisioning flow establish enrollment authority.

The channel interface exposes mode, carrier, scope, handle, epoch and a
separately reported fresh-confirmation signal. Only confirmed evidence reaches
host policy, together with opaque hello credentials, including empty
credentials. Host policy owns root-identity verification, current-enrollment
checks and principal agreement; a successful handshake, a lookup result or a
transport confirmation does not perform those checks automatically. Empty
credentials never authorize automatically, and a default method policy denies
access.

```text
NO_CHANNEL -> HANDSHAKING -> CHANNEL_ESTABLISHED -> Syntra CONNECTED
                 |                                   |
                 +-- failure -> discard/close        +-- hello validation
                                                         + policy -> ready
```

The responder's local completion after writing message two is not evidence
that the initiator received it. No existing core state or wire variant is
added by these local channel states. The host's client-record confirmation
gate remains in force before any protected delivery even if local channel
establishment has finished.

## 3. Records and bounded resources

**SNTR-SC-007** — After Noise `Split()`, each role MUST use independent
send/receive cipher states, the standard Noise transport message operations,
and empty associated data. A ciphertext MUST be at most 65,535 bytes including
its 16-byte tag; plaintext MUST be at most 65,519 bytes. Carrier limits may
reduce these bounds. Clear carrier headers are not described as authenticated
AD under this standard construction. A change to that construction requires
an explicitly reviewed, separately identified variation.

**SNTR-SC-008** — Adapters MUST enforce carrier/record bounds before
allocation and authenticate a whole record before consuming any plaintext.
Reconstructed Syntra envelopes MUST preserve the default 1,048,576-byte
serialized-frame limit or a documented lower limit. Segment/reassembly
buffers and aggregate incomplete frames MUST be bounded; no partial envelope
may reach decode/dispatch. Record boundaries are not necessarily envelope
boundaries, and small valid encrypted records do not waive resource caps.

**SNTR-SC-009** — Both roles MUST NOT reuse a traffic-key/nonce pair, reset
a nonce under the same key, copy cipher state to another channel, or migrate
it between carriers. Each new channel MUST start with a fresh handshake.
Nonce exhaustion MUST terminate the channel. The SC1 ceiling is renewal before
24 hours or `2^32` protected records in either direction; stricter deployment
limits are permitted. The lifetime clock includes establishment and continues
while idle or suspended. These are profile policy limits, not Noise limits.
Renewal is a new channel with a fresh handshake and explicit recovery
negotiation where supported, not a custom in-place rekey or resume protocol.

**SNTR-SC-010** — Both roles MUST fail closed on handshake, context or
authentication failure: no unauthenticated plaintext may reach the core.
Ordered-carrier record authentication failures MUST terminate the channel
without resynchronization. A datagram binding MUST discard invalid records
without advancing replay/endpoint/application state and define bounded abuse
handling; unauthenticated input MUST NOT unconditionally tear down a valid
channel. Errors/logs MUST NOT contain AKs, private keys, raw credential
payloads or private store diagnostics.

**SNTR-SC-011** — Both roles MUST bound absolute channel establishment,
record/frame assembly, write-stall and close times; aggregate connections,
unauthenticated handshakes/crypto workers, queued bytes/count and reassembly
memory MUST also be bounded. Trickle input MUST NOT reset absolute deadlines.
Deployments MUST document budgets and apply backpressure or reject admission,
not retain unbounded work. The SC1/WSS defaults are: 15 seconds for the total
dial/TLS/Upgrade/SC1/readiness attempt, 5 seconds for channel establishment and
first-record confirmation, 30 seconds for the next complete record, 30 seconds
for frame assembly, 10 seconds for one frame's encrypted output, and 1 second
for close/owner-task join. Each value is positive and no greater than 24 hours;
deployments MAY choose shorter values. Pending operations default to 32 per
direction including active work, with a maximum of 1,024 and immediate busy
refusal beyond admission. Writer queue capacity defaults to 256 frames and
must be 1–1,024. [noise-bindings.md](../transports/noise-bindings.md) §8 owns
the complete table and the aggregation duties.

## 4. Failure, close, and reconnect

**SNTR-SC-012** — An ordered carrier MUST serialize complete ciphertexts
and preserve partial-write offsets. Once a send consumes a nonce, its
ciphertext MUST be retained and emitted in order or the channel aborted;
cancellation MUST NOT splice another frame into unfinished output. Shutdown
MUST stop admission, drain only within a close budget, settle pending callers,
release buffers and terminate owned work. Truncated records/frames MUST NOT
be dispatched. EOF at a complete boundary MUST NOT be represented as
authenticated proof of orderly completion or application success.

The implemented host writer owns FIFO output snapshots after readiness, bounded
to 256 frames / 8 MiB including active output. Saturation terminates with
`RESOURCE_EXHAUSTED`; the host loop continues dispatch, cancellation and deadline
processing during stalls. Host write timeout defaults to 5 seconds but accepts
any positive configured value; this is separate from the adapter's maximum
5-second write deadline. Method authorization returning `UNAUTHENTICATED`
attempts actual-send denial drain for up to 200 ms; enrollment-watchdog failure
and explicit principal disconnect close directly. Writer join is 1 second
after `Close` returns. Abortive close requires cancellation-compliant
I/O/store callbacks; it cannot forcibly kill them. These are not the core's
1-second callback grace or the server's shutdown budget.

**SNTR-SC-013** — Initiators and hosts MUST select the channel mode and
carrier explicitly. Authentication or lookup failure MUST NOT trigger an
automatic retry using bootstrap, plaintext, another suite or another carrier.
New Noise mappings MUST NOT reuse the existing TLS/TCP or WS/WSS profile
identifiers or silently change their message format.

**SNTR-SC-014** — Both roles MUST treat renewed device authorization as
fresh authentication for a new channel, not automatic logical-session
resumption. In-flight RPC loss remains an unknown outcome where applicable;
RPC replay, event recovery, subscription restoration and cross-carrier
session attachment require their own explicit contracts. A live channel
does not prove current credential validity, committed progress, idempotency
or durable cursor acknowledgement.

**SNTR-SC-015** — Documentation and implementations MUST NOT claim this
profile provides post-quantum security, application E2EE, metadata anonymity,
live-endpoint compromise protection, measured performance superiority,
independent audit, implementation support or conformance without appropriate
evidence. Forward-secrecy statements MUST state fresh/secret ephemeral and
disposal assumptions. Production defaulting requires an accepted policy and
security review of the complete composition, not just the Noise primitives.

## 5. Cost accounting and assurance limits

With empty payloads, each selected Noise handshake message is 48 bytes.
The canonical v1 context is 38–292 bytes. M1 is 86–340 bytes and M2 is 48
bytes, for a complete 134–388-byte exchange before carrier framing. SC1/TCP
adds two two-byte prefixes, for 138–392 bytes. The often cited 104-byte
returning figure is 96 Noise bytes plus an eight-byte handle; it is not a
complete handshake. Carrier establishment, new attempts and client
confirmation are additional. Syntra `hello`/`ready` and enrollment exchanges
are additional messages.

One handshake RTT excludes carrier establishment and Syntra readiness.
Asymmetric-operation counts do not measure CPU, energy or binary footprint.
The canonical v1 context/carrier bytes and normative resource defaults are
specified in [noise-bindings.md](../transports/noise-bindings.md). The Rust
implementation records local execution evidence in its `AUDIT.md` and
`docs/implementation-status.md`; in-memory benchmarks do not establish
TLS-relative performance. No independent library certification, conformance
pass or security audit is claimed. Enrollment issuance, durable
storage/transactions and rotation workflows, independent vectors and
interoperability, mobile/recovery evidence and independent composition review
remain release gates. The profile is accepted; a stable release is not.

## References

- [Noise Protocol Framework](https://noiseprotocol.org/noise.html), revision 34:
  §§3, 5–7, 9, 11, 13–14.
- [Device authorization](device-authorization.md), [carrier bindings](../transports/noise-bindings.md),
  [acceptance plan](../../conformance/plans/secure-channel.md).
