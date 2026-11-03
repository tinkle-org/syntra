# Syntra 1.0 — Connection

A connection establishes a protected channel, agrees a wire version and binds
one host-verified principal. This page defines readiness, authentication outcomes
and connection lifetime. [Security](security.md) defines channel cryptography and
authorization; [transports](transports.md) defines carrier bytes and time limits;
[wire format](wire-format.md) defines envelope validation; [RPC](rpc.md) defines
call outcomes. BCP 14 keywords are normative.

The wire version is `Frame.version = 1`, in protobuf namespace `syntra.v1`.
Every carrier requires Noise. Production uses explicitly permitted encrypted
TCP or WSS; WSS also requires verified TLS 1.3 and a validated Upgrade before
Noise. WS is restricted to explicitly enabled loopback development. Carrier and
enrollment admission are deny-by-default under [transports](transports.md#1-protocol-and-carrier-selection).

## 1. Establishment and states

**SNTR-HS-001** — Establishment MUST follow these phases in order, without
skipping checks or continuing a failed attempt:

```text
Carrier setup → Noise → encrypted ClientHello and fresh client confirmation
    → version agreement → host authentication and same-principal checks
    → ServerReady → active connection → closing → closed
```

The labels `CONNECTED`, `NEGOTIATING`, `AUTHENTICATING`, `ACTIVE`, `CLOSING`
and `CLOSED` describe these protocol phases.
`CONNECTED` begins at role-local Noise completion. Negotiation and authentication
precede readiness; only an active connection admits application work.

The initiator verifies M2 before sending credentials. Host M2 emission does not
confirm the client. The first client plaintext MUST begin with exactly one framed
`ClientHello`. It may span records, but its completing record MUST end at the
hello boundary, with no complete or partial trailing envelope. The host's first
envelope is `ServerReady`, never `ClientHello`.

| Direction | Envelope | Meaning |
|---|---|---|
| Initiator → host | `Frame{version=max_version, request_id=0, hello{min_version,max_version,credential}}` | Offer a version range and opaque credential |
| Host → initiator | `Frame{version=selected, request_id=0, ready{connection_id}}` | Version accepted and principal bound |
| Either side | Native carrier termination | Establishment failed; no rejection envelope |

**SNTR-HS-002** — Each endpoint MUST start its bounded core handshake deadline
at its own Noise completion: verified M2 for the initiator, completed M2 emission
for the responder. It runs through negotiation and authentication without reset
on partial input or phase changes. No synchronized peer clocks are required.
The [transport limits](transports.md#6-limits-and-deadlines) also apply:
Noise establishment plus first encrypted hello and fresh confirmation share one
absolute **5-second** limit; total establishment through readiness has a
**15-second** limit. These limits may be shortened, never extended. The core
deadline grants no extension. A timeout before core establishment is a setup
failure.

**SNTR-HS-003** — The initiator MUST send the hello shown above. The host MUST
validate the version range before credential semantics. No supported overlap
means local `UNIMPLEMENTED` and terminal close, not a wire error. Hello carries
no capability negotiation.

**SNTR-HS-010** — The host MUST select the highest intersection of its supported
versions and the offered range. Before agreement `Frame.version` is the initiator
maximum; after agreement it is the selected version.

**SNTR-HS-004** — The host MUST complete the authentication checks in §3 before
sending exactly one ready and becoming active. Failure closes the connection.
`connection_id` identifies only this connection; it is not authentication or
session authority.

**SNTR-HS-005** — New requests, cancellation and host notifications MUST wait
for `ACTIVE`. Every subsequent frame MUST use the selected version for the
connection's lifetime.

**SNTR-HS-011**, **SNTR-HS-021** — Failure to reach readiness by the effective
handshake deadline MUST abort the attempt with local `DEADLINE_EXCEEDED`.
Both peers enforce a documented bounded deadline; authentication cannot extend
it, and timeout never implies success.

**SNTR-HS-012** — Pre-active application frames, a second hello, ready received
by a host, or hello/ready after activation MUST fail the connection. The offending
frame MUST NOT be dispatched, delivered later or treated as subscription
establishment. No zero-ID result, error-bearing ready, second hello or notification
may carry rejection. Structural validation and unknown-body precedence follow
[wire format](wire-format.md#2-bounded-raw-validation-and-first-error-precedence).

| Phase | Input or event | Disposition |
|---|---|---|
| Connected | First valid hello | Negotiate, then authenticate; continue existing deadlines |
| Negotiating | No version overlap | Local `UNIMPLEMENTED`; close |
| Authenticating | Policy accepts | Send one ready; active |
| Before active | Denial, expiry or loss | Close under §2; no application delivery |
| Before active | Application frame or repeated/wrong-role handshake frame | Local `FAILED_PRECONDITION`; discard and close |
| Any phase | Sole structurally valid unknown body | Local `UNIMPLEMENTED`; close under wire precedence |
| Active | Lawful request, cancel, result or notification | Process under RPC and wire rules |
| Active | Hello or ready | Local `FAILED_PRECONDITION`; close |
| Active | Unknown/late result or cancel | Ignore with bounded diagnostics; no reply or call revival |
| Closing | New work | Reject admission; never dispatch |
| Closing | Valid in-transit notification | Accept within receive bounds or account loss; never complete an RPC |

**SNTR-HS-006** — Closing MUST stop new RPC admission and settle unfinished
calls once under [RPC terminal rules](rpc.md#3-one-elapsed-deadline-and-one-terminal-outcome).
Remaining calls receive `UNAVAILABLE` or `CANCELLED`, subject to already-selected
outcomes and deadline precedence. After closure, connection-local state is
discarded apart from bounded diagnostics. Shutdown follows §5.

**SNTR-HS-013** — Either peer MAY initiate graceful close from active operation.
It MUST stop new work and use an absolute bounded grace deadline. Pending output
and control traffic MUST NOT reset grace or extend call deadlines. Immediate
teardown may skip drain; security failures may abort without drain.

**SNTR-HS-014** — Unexpected transport loss MUST be surfaced as closure and
`UNAVAILABLE` to affected unfinished callers. Already-selected terminal outcomes
remain terminal. Loss is neither application success nor rollback.

**SNTR-HS-015** — Update recovery MUST be explicit under [recovery](recovery.md).
It restores neither outstanding RPCs nor the connection's identity binding.

### Role obligations

**SNTR-HS-020** — The initiator MUST send exactly one hello first, with nonzero
`min_version ≤ max_version`, and await ready before application frames. On failure
it MUST close, without automatic version, mode, pin or carrier downgrade. A
subsequent attempt uses a new connection.

**SNTR-HS-030** — The host MUST validate hello shape and bounds before policy,
select or reject deterministically, and produce one establishment outcome:
ready on success, native termination on failure.

**SNTR-HS-031** — Hosts MUST cap concurrent handshakes and attempt rates. Excess
admission is local `RESOURCE_EXHAUSTED` and rejection/close, never a pre-active
response envelope.

**SNTR-HS-040** — Every handshake failure MUST be terminal for that connection.
Re-handshake on the same carrier connection is forbidden.

## 2. Failure reporting

The detecting endpoint records a typed local cause. Its peer observes only the
native termination actually received and MUST NOT infer a precise remote error
from an indistinguishable close. No diagnostic payload or particular WebSocket
close code is promised. Transport failure is not a host-sent `RpcResult`.

| Detecting-side condition | Local cause | Peer-visible evidence |
|---|---|---|
| Malformed wire/hello shape, reserved tag or invalid raw multiplicity | `INVALID_ARGUMENT` | Native termination only |
| Frame or admission bound exceeded | `RESOURCE_EXHAUSTED` | Native termination only |
| No version overlap or sole valid unknown body | `UNIMPLEMENTED` | Native termination only |
| Wrong phase/direction or repeated hello | `FAILED_PRECONDITION` | Native termination only |
| Invalid, expired, revoked or missing required credential | `UNAUTHENTICATED` | Generic termination; no credential-validity oracle |
| Valid identity with insufficient connection access | `PERMISSION_DENIED` | Generic termination; no denial sub-reason |
| Local absolute deadline expired | `DEADLINE_EXCEEDED` | Teardown; no evidence the peer's timer expired |
| Noise context, pin or record authentication failure | Sanitized channel failure | Native termination; no unauthenticated plaintext |
| TLS/Upgrade failure | Setup-phase failure | TLS/HTTP/native signal; no M1 after failed validation |
| Unexpected loss | `UNAVAILABLE` for unfinished calls | No remote verdict inferred |

Absent better local evidence, the peer reports `UNAVAILABLE`. An HTTP error here
is an Upgrade failure. Wire validation precedence, not table order, selects
concurrent input errors.

## 3. Authentication interface

**SNTR-AUTH-001** — The host MUST verify credentials using its authentication
policy. Syntra defines opaque carriage and outcomes, not credential syntax or an
identity service. The handshake has no mechanism identifier, advertisement,
selection or challenge field.

**SNTR-AUTH-002** — Initial credentials MUST appear only in encrypted
`ClientHello.credential`. Documented follow-ups use opaque RPC payloads after
readiness. Credentials MUST NOT appear in URLs, Upgrade headers, connection or
request IDs, methods, errors, logs or event metadata. Syntra MUST treat them as
opaque sensitive bytes, without persistence, interpretation or echo. Production
use requires a permitted protected carrier and all [security](security.md) checks.

**SNTR-AUTH-003** — Empty credentials are a valid anonymous attempt on the wire,
accepted only by explicit host policy. They MUST NOT implicitly select an
enrolled principal. The credential limit is **8,192 raw bytes**, regardless of
encoding. Producers MUST check before sending; receivers MUST enforce before
allocation, dispatch and policy lookup, without truncation.

**SNTR-AUTH-004** — Application-defined authentication follow-ups MUST use
generic RPC after readiness. Syntra MUST NOT interpret their payloads or silently
negotiate a mechanism; they introduce no pre-active frame types.

**SNTR-AUTH-005** — Authentication success MUST bind a principal to this
connection at ready. Each method still requires authorization; ready grants no
unrestricted permission or recovery guarantee.

**SNTR-AUTH-006** — Denial MUST use local `UNAUTHENTICATED` for missing required,
invalid, expired or revoked credentials, or `PERMISSION_DENIED` for a valid identity
with insufficient access. Public reporting MUST NOT distinguish unknown identity,
wrong secret, expiry or revocation, or expose credential/store diagnostics.

**SNTR-AUTH-007** — An active connection MUST have at most one fixed principal,
used for all authorization. Unverified hello identity, public handles, Origin,
forwarded headers or successful key lookup MUST NOT replace or merge with it.

Host authentication combines trusted connection-scoped channel evidence with
the explicit opaque credential, including empty bytes. Before ready, the host
checks current enrollment, independently verified application identity, scope
and same-principal agreement under [security](security.md#pre-ready-identity-and-enforcement).
Noise success alone does not perform these checks. Method and subscription
authorization precede effects.

**SNTR-AUTH-008** — Hosts MUST enforce expiry and revocation. Withdrawal MUST
reject affected unfinished work with `UNAUTHENTICATED`, settle calls once under
RPC terminal rules, cut off protected delivery and close the connection. The
initiator MUST treat withdrawal as terminal for that binding. Enrollment
enforcement follows `SNTR-DAUTH-018/019`: at most **300 seconds** from authoritative
revocation commit, with a **60-second operational target**, including idle
connections. Failed or stale validity checks deny admission; cached authority
cannot exceed its declared freshness bound or extend that maximum.

**SNTR-AUTH-009** — Handshake denial MUST follow §2 without a wire error.
After readiness, an ordinary `PERMISSION_DENIED` MUST use a correlated error and
leave the binding and connection usable. A method verdict of `UNAUTHENTICATED`
withdraws the binding under `SNTR-AUTH-008`. Bounded denial drain neither delays
security enforcement nor proves delivery.

**SNTR-AUTH-010** — A bound principal MUST NOT change on the same connection.
A second hello is connection-fatal. A lawful nonzero-ID RPC attempting principal
change returns `FAILED_PRECONDITION`, leaving the binding and connection usable.
Authentication follow-ups do not rebind it; a new principal requires a fresh
protected connection and hello.

**SNTR-AUTH-020** — Initiators MUST obtain credentials through authorized
application or out-of-band paths, use permitted carriers, omit credential
diagnostics, discard rejected handshake state and use bounded backoff without
automatic downgrade.

**SNTR-AUTH-021** — Initiators MUST NOT assume a human principal.
`UNAUTHENTICATED` requires fresh authority or credential recovery;
`PERMISSION_DENIED` requires authorization change, not identical retry.

**SNTR-AUTH-030** — Hosts MUST validate shape and bounds before policy, compare
secrets in constant time where applicable, rate-limit attempts and prevent
protected operations before authentication. Method authorization MUST deny by
default; permissive behavior requires explicit opt-in.

**SNTR-AUTH-031** — Hosts MUST isolate principals across connections. Credentials
or state from one connection MUST NOT authorize another's calls or leak through
connection IDs or errors. Each new connection authenticates afresh.

## 4. Connection versus session

**SNTR-SESS-001** — A session begins at readiness, without a separate session
handshake. Application associations remain opaque to Syntra.

**SNTR-SESS-002** — `ServerReady.connection_id` MUST be fresh, opaque,
unguessable with at least **128 bits of entropy**, and scoped to one connection.
Its valid UTF-8 representation MUST be **1–128 bytes**, with no encoded principal
or session information. It MUST NOT be accepted as a credential, resume token,
session handle or client-selected state. It is diagnostic only.

**SNTR-SESS-003** — Session lifetime MUST equal connection lifetime. Only
application-defined durable state survives closure; Syntra defines no
logical-session resumption.

**SNTR-SESS-004** — Graceful or abrupt closure MUST end the session and discard
connection-local state. Loss leaves unfinished calls `UNAVAILABLE` under RPC
terminal rules.

**SNTR-SESS-005** — Hosts MAY impose stricter connection lifetimes within the
security ceiling. Authentication withdrawal uses `UNAUTHENTICATED`; shutdown
uses `UNAVAILABLE`. Lifetime expiry MUST NOT be reported as successful work.

**SNTR-SESS-006** — Peers MUST reject attempted resumption of a logical session.
A connection ID or presented resume data MUST NOT restore authority. Rejection
uses `FAILED_PRECONDITION` or `UNAUTHENTICATED` under the phase's signaling rules.

**SNTR-SESS-007** — A session MUST retain its ready-bound principal. Principal
change requires a new connection and handshake; withdrawal ends the binding.

**SNTR-SESS-008** — Reconnect MUST NOT restore RPCs, subscriptions or
connection-local cursors. Fresh readiness and explicit recovery/re-subscription
are required. Durable checkpoints have only their [recovery](recovery.md) meaning.
Reusing valid enrollment is fresh authentication.

**SNTR-SESS-010** — Initiators MUST reauthenticate on every connection and
MUST NOT present `connection_id` as authority or retain it beyond
connection-lifetime diagnostics.

**SNTR-SESS-011** — Initiators MUST explicitly re-establish subscriptions and
negotiate recovery after new readiness, without automatic RPC replay.

**SNTR-SESS-020** — Hosts MUST generate fresh connection diagnostics and reject
their use as authentication or resumption authority.

### Replacement and mobile elapsed time

A replacement connection requires fresh Noise state, version agreement and host
principal validation. Results and notifications from a retired connection cannot
complete replacement calls, confirm its recovery or establish its subscriptions.
The old connection's callers settle once; closure does not prove remote work
stopped or rolled back. No request or mutation transfers or replays automatically.

Reconnect is explicit, with finite attempt and elapsed-time budgets and capped,
jittered backoff. Suspension does not accumulate attempts. Locally known
credential or endpoint-validation rejection requires explicit recovery, never
fallback. A generic remote close is not an authentication diagnosis.

The [RPC elapsed-deadline rules](rpc.md#3-one-elapsed-deadline-and-one-terminal-outcome)
also apply during suspension: account elapsed time, authorization validity and
channel age before buffered delivery or sends. Unknown elapsed continuity fails
live work and requires a fresh connection. Traffic cipher state and monotonic
timestamps are not persisted for cross-process reuse. Network-change hints grant
neither reachability nor trust; Syntra promises no activity during OS suspension.

## 5. Shutdown, output and liveness

Graceful close stops admission, drains eligible output only within the absolute
grace deadline, settles remaining callers once and closes the carrier within
that deadline. Drain leaves positive bounded time for carrier teardown; insufficient time
means abort. Security failures may abort at any point. Already-selected outcomes
remain terminal; close or drain timeout proves neither delivery nor stopped
application effects. [RPC](rpc.md#fifo-output-and-shutdown) defines ordered output;
[transports](transports.md#6-limits-and-deadlines) defines write and close
limits. There is no protocol close envelope.

Complete authenticated frames indicate transport progress, not authorization
renewal, application completion or durable checkpoint acknowledgment. Carrier
liveness follows [transports](transports.md); Syntra has no additional mandatory
heartbeat.
