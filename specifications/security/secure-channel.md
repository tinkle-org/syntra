# Syntra Secure Channel v1 — Shared channel proposal

- Status: Proposal only — Draft RFC 0007; not an accepted production profile
- Date: 2026-10-27
- Owner: [RFC 0007](../../rfcs/0007-secure-channel-device-authorization.md)
- Scope: Channel establishment and record security, independent of carrier I/O
- Proposed requirements: `SNTR-SC-001`–`SNTR-SC-015`

This is the selected design direction, not shipping support or a security
certification. BCP 14 keywords below describe proposed obligations only.
Existing [transport-security.md](transport-security.md) and ADR-008 remain
the baseline until the RFC is accepted. The [device authorization draft](device-authorization.md)
owns enrollment/lifecycle; the [carrier draft](../transports/noise-bindings.md)
owns byte mappings. [Planned acceptance cases](../../conformance/plans/secure-channel.md)
are not executable conformance results.

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
carrier binding, intended endpoint scope/server identity, and, for returning
devices, authorization handle and epoch. The AK MUST enter through the Noise
PSK input, never the prologue. Exact unambiguous byte encodings and how epoch
and server-key selection reach both peers are RFC freeze blockers. A local
configuration mismatch MUST fail rather than invoke another mode.

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

**SNTR-SC-006** — The initiator MUST verify the second Noise message before
sending Syntra `hello`. The responder MUST authenticate at least one client
transport record under the new keys before treating the client as freshly
confirmed or enabling protected application effects/sensitive delivery. The
encrypted `hello` may supply this confirmation. The host MUST then evaluate
the enrollment's current principal/scope and the Syntra handshake before
`ready`; the client MUST wait for `ready` before protected RPCs. PSK possession
does not bypass method authorization. For bootstrap, application credentials
or an explicitly authorized provisioning flow establish enrollment authority.

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
Nonce exhaustion MUST terminate the channel. The proposed stricter SC1
ceiling is renewal before 24 hours or `2^32` records in either direction;
these numerical policy choices require acceptance and are not Noise limits.
Renewal is a new channel, not a custom in-place rekey/resume protocol.

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
not retain unbounded work. Numeric interoperable defaults are acceptance
blockers. The existing Syntra handshake deadline begins after channel
establishment; a separate total-attempt budget bounds all phases.

## 4. Failure, close, and reconnect

**SNTR-SC-012** — An ordered carrier MUST serialize complete ciphertexts
and preserve partial-write offsets. Once a send consumes a nonce, its
ciphertext MUST be retained and emitted in order or the channel aborted;
cancellation MUST NOT splice another frame into unfinished output. Shutdown
MUST stop admission, drain only within a close budget, settle pending callers,
release buffers and terminate owned work. Truncated records/frames MUST NOT
be dispatched. EOF at a complete boundary MUST NOT be represented as
authenticated proof of orderly completion or application success.

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

## 5. Cost accounting and limits of this draft

With empty payloads, each selected Noise handshake message is 48 bytes.
Bootstrap therefore uses 96 Noise bytes. The often cited returning total of
104 bytes is 96 plus an eight-byte handle, not the complete frozen handshake:
context fields, carrier framing, retries and confirmation may add bytes.
Syntra `hello`/`ready` and enrollment exchanges are additional messages.

One handshake RTT excludes carrier establishment and Syntra readiness.
Asymmetric-operation counts do not measure CPU, energy or binary footprint.
No backend/library is selected or certified here. The RFC's wire, lifecycle,
resource and verification blockers prevent shipping this as a production
replacement for the current security profiles.

## References

- [Noise Protocol Framework](https://noiseprotocol.org/noise.html), revision 34:
  §§3, 5–7, 9, 11, 13–14.
- [Device authorization](device-authorization.md), [carrier bindings](../transports/noise-bindings.md),
  [acceptance plan](../../conformance/plans/secure-channel.md).
