# RFC 0013: Noise-protected HTTP carriers and trusted TLS streams

- RFC: 0013
- Title: Noise-protected HTTP carriers and trusted TLS streams
- Author(s): Syntra contributors
- Status: Draft
- Date: 2026-11-03
- Target version: Syntra 1.0 pre-release, subject to compatibility decision
- Relates to: [transports](../specifications/transports.md), [security](../specifications/security.md), [connection](../specifications/connection.md), [RPC](../specifications/rpc.md), [carrier registry](../conformance/profiles.yaml), [RFC process](README.md)
- Reviewers: Human protocol/security reviewer unassigned; AI advisory review recorded separately
- Maintainer consent: oscarlaw confirmed approval with self-approval disclosed; public decision pending

## 1. Summary

This proposal defines production-capable HTTP/1.1 and HTTPS/1.1 carriage of the
same mandatory Syntra Noise channel, using bounded POST uploads and POST long
polls. It also defines a trusted, in-process TLS-provider boundary for HTTPS and
WSS clients and hosts. Native integrations would support owned sockets,
application-provided TLS streams, asynchronous reactors and timers, explicit
endpoint failover, bounded reconnect backoff, SOCKS5 and HTTP CONNECT tunnels,
and forwarding pause/resume. None of these mechanisms bypasses Noise, host
authentication, authorization or current validity checks.

This proposal specifies wire behavior, role obligations and observable
composition boundaries. It does not prescribe a programming language, package
layout, callable interface or scheduling framework.

This document is a proposal, not a protocol authority. Its BCP 14 keywords
describe proposed obligations only. Requirement labels beginning `R13-` and test
labels beginning `R13-T` are local to this draft, not registered requirements or
conformance cases. The sole active maintainer's confirmation is recorded in
[Decision 0003](../docs/decisions/0003-http-tls-consent.md), including self-approval.
The public RFC/PR decision and human security review required by governance
remain pending. Implementations cannot ship this behavior or cite this draft for a
conformance claim under the [RFC lifecycle](README.md#lifecycle).

## 2. Motivation

Some deployments permit ordinary HTTP requests but cannot use an Upgrade or a
long-lived raw bidirectional stream. A Syntra connection still needs ordered
bidirectional records, a real hello/ready exchange, cancellation, notifications,
and loss semantics that do not imply safe RPC replay. HTTP status codes and
connection pooling cannot supply these properties.

Embedders also need to choose their established TLS implementation and manage
certificates without surrendering stream ownership or treating a network claim
as TLS verification. The current direct-host WSS rule needs an explicit trust
boundary for a TLS provider that runs inside that host or client process.
Socket dialing, proxies and timers need corresponding bounded contracts.

The reference at base commit
`3f7e8ea037fefcc5c86101d23e7722c83e28a0d3` lists only carriers 1, 2 and 3.
HTTP request/response is not an available binding at that revision. This draft
proposes the additional mapping without changing the current reference, source
IDL, registry, candidate contract or accepted vectors.

Repository issue/PR searches for `HTTP TLS carrier` found no issue and returned
related PRs 12, 15, 16, 18 and 23; none supplies acceptance of this proposal.
Reviewers still need to check concurrent proposals before assigning numbers.

## 3. Proposal

### 3.1 Proposed carrier allocation and ownership

| Proposed byte | Proposed binding name | Deployment | Additional outer security |
|---:|---|---|---|
| 4 | `http-h1-post-poll-noise` | Production, explicitly permitted | No TLS required; independently provisioned Noise pin required |
| 5 | `http-h1-post-poll-verified-tls13-noise` | Production, explicitly permitted | Verified direct-host TLS 1.3 or higher plus independent Noise pin |

These bytes are **proposed, not allocated or registered**. The checked
[registry](../conformance/profiles.yaml) and
[candidate input](../compatibility/syntra-1.0.json) contain only 1/2/3, so 4/5
have no conflict in this checkout. Two values are justified because authenticated
context must distinguish a deployment requiring outer TLS from one without it;
a URL, header or runtime feature cannot change that requirement. WSS remains 3.
No byte is assigned for a TLS library, proxy, reactor or encryption switch.

**R13-01 (selection; both roles).** A selected HTTP binding MUST use its proposed
carrier byte in the existing canonical context and the existing Noise patterns,
prologue, handshake, records and inner frame stream. Every listener and
enrollment policy MUST explicitly permit that binding, mode, selector and scope
before lookup. Empty/default binding sets MUST deny admission. Selecting HTTP,
HTTPS, WSS, a proxy or a TLS provider MUST NOT disable Noise or enable another
binding. Carrier/format/mode fallback MUST NOT be automatic. Violations terminate
before credential lookup or protected dispatch.

The context encoder remains the single source for field order and scope limits;
this draft adds no offsets or second context format. M1 is the context followed
by the standard first Noise flight; M2 is the standard second flight. Both
payloads remain empty. Standard transport ciphertexts protect the existing
`u32BE(F) || Frame` stream. Existing frame validation and error precedence apply,
including unknown metadata versus future body handling and forbidden tags.

No `.proto` diff is proposed. The `syntra.v1` package, `Frame.version = 1`, field
numbers, reservations, recovery service paths and `profile_version` fields stay
unchanged. There is no HTTP credential header, synthesized hello, new ready
field, close envelope or HTTP-specific RPC session.

### 3.2 Owner edits requiring acceptance

| Owner | Proposed follow-up after acceptance |
|---|---|
| `specifications/transports.md` | Define bytes 4/5, HTTP mapping, association, limits and proxy/failure rules; preserve existing carrier bytes and common encoding |
| `specifications/security.md` | Permit explicitly authorized HTTP/HTTPS enrollment bindings; define trusted in-process TLS termination; retain rejection of forwarded assertions |
| `specifications/connection.md` | Include HTTP setup in establishment and native HTTP termination in loss reporting; retain one principal and one session per fresh Noise connection |
| `specifications/rpc.md` | Cross-reference HTTP output ownership and uncertainty; no change to correlation, terminal selection or replay prohibition |
| `conformance/manifest/requirements.yaml`, manifests and `profiles.yaml` | Register accepted requirements/carriers and role-specific cases with evidence prerequisites |
| Context fixtures and `compatibility/syntra-1.0.json` | Add accepted carrier-positive/negative fixtures and an explicitly reviewed candidate revision without rewriting existing fixture bytes |
| `CHANGELOG.md` under `Unreleased` | Describe only behavior actually approved and activated |

The isolated [candidate bundle](0013-http-tls/README.md) contains the machine
contract, proposed registry/case definitions, context and HTTP fixtures, and owner
deltas for review. It does not activate current owners or register claimable
carriers. Activation needs a public decision, human security review and
synchronized owners; downstream input pins are separate, reviewed changes.

### 3.3 Connection sequence

```text
Initiator                                      Host
    | resolve/dial upload stream U (proxy/TLS if configured)
    | POST /syntra/1.0/http/open : M1 ------------>|
    |<---- 201 : M2; Syntra-Route: H -------------| reserve association
    | verify M2; dial poll stream D (same endpoint/provider policy)
    | POST /syntra/1.0/http/poll : empty; H; poll=0 -->| bind D once
    | POST /syntra/1.0/http/send : encrypted hello; H; upload=0 -->|
    |<---- 204; upload=0 ------------------------| complete record admitted to carrier input
    |                                            | Noise verifies and assembles full hello
    |<---- 200 : encrypted ready; poll=0 --------| current host policy
    | ACTIVE only after validating ready         |
    | send POSTs on U; sequential long polls on D |
    |<==== ordered encrypted results/notifications ===|
    | close / loss / pause / uncertainty          |
    | discard association and both cipher states |
    | a later attempt starts fresh; no RPC replay |
```

U and D are separate persistent HTTP/1.1 byte streams, each backed by its own
end-to-end TCP connection (and TLS connection for HTTPS). The poll may be issued
before or concurrently with hello upload; it does not grant authority. A hello
or ready spanning records uses successive exchanges, with the common strict
first-hello rule and the same absolute establishment budgets.

## 4. Detailed design

### 4.1 Endpoint authority and HTTP syntax

**R13-02 (authority; both roles).** The initiator MUST select one provisioned
endpoint descriptor containing scheme, DNS A-label hostname or IP literal,
effective port, Noise pin set, exact service scope, binding, TLS policy if
applicable and explicit direct/proxy route. Userinfo, query, fragment, dynamic
path prefixes and credentials in the URL MUST be rejected. The four paths below
are exact and case-sensitive. HTTP uses `http` and default port 80; HTTPS uses
`https` and default port 443. The wire `Host` value MUST be the descriptor's
canonical authority with effective port included, bracketed for IPv6. DNS names
use lowercase A-labels without a trailing dot; scope bytes are not normalized.
The host MUST validate one `Host` against its configured authority allowlist
before association lookup. Network headers, DNS answers, route handles and
redirects MUST NOT teach new endpoint authority, pins or scope.

The canonical origin is `(scheme, canonical host, effective port)`. U and D use
the same selected descriptor, host owner and policy generation. Load balancing
can route bytes to that owner, but a second owner cannot import cipher state.
Source addresses and DNS affinity are routing/abuse signals, never identity.

For R13-02, a policy generation is a role-local immutable snapshot of the
selected authority, route, binding, pin set, scope and applicable TLS policy.
Configuration changes create a new generation rather than mutate a selected
snapshot. U and D MUST remain bound to the same snapshot throughout establishment;
equal authorities or deadlines alone MUST NOT establish that binding. If the
selected generation is withdrawn before establishment completes, the role MUST
retire the attempt before further credential release or protected dispatch.
Publishing a successor does not itself withdraw a still-permitted generation.
Snapshot retention MUST NOT freeze time validity, revocation or other current
authorization checks. Generation identity is local evidence, not an HTTP header,
wire field or authentication credential.

**R13-03 (HTTP framing; both roles).** Requests MUST be POST with origin-form
targets and HTTP/1.1; responses MUST be HTTP/1.1. Each request and each non-204
response MUST have exactly one canonical decimal `Content-Length` (zero is `0`,
otherwise no leading zero, sign, whitespace within digits or comma list).
204 responses MUST have no body, Content-Length or Transfer-Encoding, as required
by HTTP semantics; receiving any of these is fatal. Positive bodies MUST carry
exactly `Content-Type: application/octet-stream`. Zero bodies omit Content-Type.
Transfer-Encoding, Content-Encoding, Trailer, Expect, Upgrade and request `TE`
MUST be rejected; no chunking, compression, multipart, streaming body, pipeline,
HTTP/2, HTTP/3 or close-delimited body is defined. Senders MUST NOT use them.
Receivers MUST reject ambiguous framing, duplicate singleton headers, obs-fold,
invalid field syntax, CR/LF injection and excess bytes without resynchronizing.
Both roles MUST enforce §4.2's per-operation body, status and association-header
table before processing its contents, rejecting missing required or inapplicable
association headers and incorrect Content-Type.
Both roles MUST preserve bytes read ahead for a subsequent legal message; bytes
of a second request before the prior response completes are forbidden pipelining.

Header names are ASCII case-insensitive; values defined here are case-sensitive.
Each `Syntra-*` header defined in this RFC is a singleton. Unknown `Syntra-*`
headers are rejected to avoid implicit extension negotiation. Other lawful,
bounded HTTP headers may be ignored, but cannot affect identity or framing.
Requests carry no Authorization, Cookie or Proxy-Authorization at the origin;
responses carry no Set-Cookie. Senders omit these and receivers reject them.
Proxy-Authorization is confined to §4.8's proxy handshake, outside the origin
request. Connection persistence is required; `Connection: close`, EOF or stream
replacement retires the association even at a complete HTTP message boundary.

**R13-04 (routing controls; both roles).** Both roles MUST NOT follow redirects,
perform automatic HTTP authentication challenges, retry an origin exchange,
cache, prefetch, hedge or speculatively duplicate these requests. All responses
MUST send `Cache-Control: no-store`; requests MUST send `Cache-Control: no-store` and
`Accept: application/octet-stream`. Origin middleware and HTTP clients MUST have
automatic retries, decompression, redirects, cookies and response caching
disabled. Hosts MUST enforce an explicit Origin allowlist or explicit rejection
policy before body/route lookup; absent Origin is permitted for native clients.
Multiple Origin values and `Origin: null` MUST be rejected. A configured allowlist
compares exact serialized origins; an absent Origin never supplies authority.
Origin, Referer, Forwarded and X-Forwarded-* MUST NOT supply authentication,
carrier selection or TLS evidence. No handle or secret is sent across origins.

### 4.2 Paths, bodies and association

| Path suffix under `/syntra/1.0/http/` | Request on stream | Required association headers | Request body | Success response |
|---|---|---|---|---|
| `open` | New U only | None | Exactly one M1 | `201`, exactly one M2; `Syntra-Route: H` |
| `send` | Bound U only | `Syntra-Route: H`, `Syntra-Upload: n` | Exactly one ciphertext record | `204`, empty; `Syntra-Upload: n` |
| `poll` | First D or bound D | `Syntra-Route: H`, `Syntra-Poll: p` | Empty | `200`, exactly one ciphertext record, or `204`, empty; both echo `Syntra-Poll: p` |
| `close` | Bound U only, serialized after sends | `Syntra-Route: H` | Empty | `204`, empty; association retired |

No route header is allowed on `open`; no upload/poll counter is allowed on other
operations than its table entry. Responses contain only the association headers
specified in the table. HTTP success confirms only that carrier operation. It
does not attest execution, durable receipt, authentication, cancellation or
application delivery. Successful open is not Syntra readiness.

**R13-05 (open; initiator).** The initiator MUST create fresh Noise state and
send M1 only after endpoint and any TLS/proxy verification. It MUST accept only
a fully framed 201 with a valid H and exact M2 length, verify M2 with its
provisioned pin, and only then encrypt hello. It MUST NOT retry M1/open, reuse U,
or release hello credentials after missing, malformed or failed M2/HTTP/TLS
validation. Any failure retires the attempt, including an unreceived 201.

**R13-06 (open; host).** The host MUST bound connection, body, rate, lookup and
cryptographic admission before accepting M1. It MUST validate context and
configured carrier/mode/selector/scope before key lookup, reserve both stream
capacity and one association slot, and produce at most one M2. H MUST be 32
independent CSPRNG bytes encoded as exactly 64 lowercase hexadecimal characters,
with no embedded identity. A collision MUST redraw at most four times, then
fail closed without overwriting a live slot; entropy failure also fails closed.
The slot MUST bind H, U, selected authority/binding/scope, policy generation,
responder state, deadlines and resource permits. A failed or abandoned response
MUST retire the slot within those deadlines, not persist it for retry.

**R13-07 (handle meaning; both roles).** H MUST be used only as a transient,
opaque association selector. It MUST NOT be treated as an authentication
credential, authorization key, application identity, diagnostic connection ID,
session/resumption token or durable recovery cursor. The host MUST NOT create
effects, bind a principal or extend a lease merely because H matches. Only
fresh Noise confirmation, full valid encrypted hello and current host-owned
credential/enrollment/same-principal policy can authorize ready. Empty credentials
MUST still reach that policy and MUST NOT imply the channel principal.

H has guessing resistance for routing, but secrecy is not principal authority.
A bearer who learns H might win the first-poll race or disrupt delivery; this is
a denial-of-service risk, not permission to decrypt, inject authenticated work,
or resume a connection. Plain HTTP exposes H, lengths and timing to the network.
This is comparable to cutting/reordering a raw TCP stream; public HTTP use
accepts that availability and metadata boundary. HTTPS protects that outer hop.
H is independent of the clear enrollment handle already present in context.

**R13-08 (stream association; host).** The first valid `poll` with H and p=0
MUST atomically bind one D to the live slot, same configured authority and host
owner. D MUST be distinct from U. U MUST accept only send/close after open;
D MUST accept only polls for its bound H. A second D, different H on a bound
stream, duplicate open, stream substitution or operation on the wrong stream
MUST retire the affected association and reject the operation. H MUST NOT permit
pooling, connection rebinding, process/owner transfer or importing state after
failure. Invalid/unknown H performs no cryptographic work and allocates no slot.
Missing first poll or hello expires under the unchanged channel deadline.

For an already bound stream, the affected association is its original slot;
presenting another slot's H MUST NOT invalidate that unrelated slot. On an
unbound D, a duplicate ownership claim on a live H retires that H's slot. The
host MUST serialize slot invalidation against body admission and output so that
no callback revives an invalidated association.

No IP-equality requirement is imposed on U/D: NAT and configured proxies can
change addresses. The fixed stream pair, owner and explicit authority checks
provide association; Noise provides authentication. Hosts reserve a bounded
unbound-stream pool and bind D before waiting, never allocate on arbitrary H.

### 4.3 Directional ordering and delivery

**R13-09 (uploads; both roles).** The initiator MUST allow only one send request
in flight on U, starting n=0 and incrementing once after each exact 204 echo.
The host MUST require the next n on U, accept a complete bounded body,
and atomically commit that entire record into the live association's bounded
carrier-input slot before returning 204. Admission MUST reserve capacity, retain
exact bytes and stream order, and reject if the association retired. A 204 MUST
NOT attest Noise authentication, higher-runtime consumption, frame validation or
effects. It MUST NOT depend on the higher runtime's decryption/processing; doing
so creates a layering cycle for a standalone record adapter. Partial input or a
full queue MUST NOT receive a success acknowledgment. The shared encrypted
driver MUST authenticate each admitted record and feed only authenticated
plaintext into bounded frame assembly before any dispatch. Authentication,
shape, policy and phase failures remain fatal under common rules, even if 204
was already sent; the host then retires both streams. These failures MUST NOT
become HTTP-carried `RpcResult` substitutes. The sender MUST NOT resend
the body on a missing acknowledgment, even if no response byte was observed.

The same carrier-input boundary admits M1 from open; its 201 still waits for
exactly one M2 from the common Noise driver. A carrier record reader can return
an admitted M1/record without waiting for that request's response to be written.
A writer sends M1 via open, M2 as the open response, client records via send and
host records via poll responses. Each operation retains its own absolute budget.
No record is admitted twice, and neither HTTP queue admission nor M2 emission
confirms a client. This allows one shared encrypted handshake/record pump rather
than a second HTTP implementation of Noise or core authentication.

**R13-10 (polls; both roles).** The initiator MUST keep at most one poll in
flight on D, starting p=0 and incrementing after each complete valid 200/204
echo. It MUST promptly issue the next poll within the five-second gap bound.
The host MUST hold one poll for at most 25 seconds, returning 200 when one
complete ciphertext record is available or 204 on an empty hold expiry. A
response MUST finish within the poll's 30-second absolute exchange deadline.
Ready records wait for complete hello/current policy; no protected host output
precedes fresh client confirmation. The host MUST select each output record
exactly once and MUST NOT retain it for redelivery on a later poll. The
initiator MUST fully validate HTTP framing and authenticate the entire record
before exposing its plaintext. Duplicate, wrong or missing counters/statuses,
partial responses and uncertain consumption MUST retire both streams.

An empty 204 is carrier liveness only, consumes no Noise nonce and carries no
Syntra frame. Neither that response nor a new poll resets an absolute channel,
record, partial-frame, call or authorization deadline. There is no polling
acknowledgment that makes retransmitting ciphertext safe.

**R13-11 (counters and records; both roles).** n and p MUST be canonical decimal
unsigned 64-bit integers, not echoed request IDs or Noise nonce encodings. A
counter mismatch, duplicate, overflow or wrap MUST terminate, never resynchronize
or replay. The host MUST require its next expected counter, advancing n after
record admission and p when committing that poll's single response; response
failure retires the association rather than undoing either counter. Each
direction MUST preserve the channel's implicit record order;
HTTP chunking, packet boundaries, counters, status and headers MUST NOT become
Noise AD or replace authentication. M1/M2/records MUST occupy exactly one body
each, with no outer u16 prefix, text/base64 wrapper, extra record or trailing
bytes. Existing encrypted inner u32 framing, hello boundary, frame ceiling,
record-count and lifetime ceilings MUST remain intact.

**R13-12 (output ownership; both roles).** Output MUST pass the existing
frame-specific emission eligibility and authorization checks once immediately
before handoff/encryption. An unsent request whose call has expired or already
terminated MUST be skipped before nonce use. After acceptance, one frame's
records MUST finish in order within one absolute ten-second output budget, or
the connection MUST abort. Record/HTTP fragments MUST NOT be re-gated, spliced,
re-encrypted or moved into another exchange after
uncertainty. Partial writes of the same immutable response/request on the same
stream may continue under the original budget; sending it again as a new HTTP
request/response is forbidden. Expiry, withdrawal or stop may abort that output,
but MUST NOT recycle its nonce. HTTP acknowledgment is not delivery attestation.

At the R13-12 emission gate, ownership of one complete selected frame MUST pass
to a single ordered output operation. A live request's remaining timeout MUST be
encoded under the existing RPC elapsed-deadline rules. A host-selected result
MUST retain its selected outcome; the originating call being terminal or its
deadline subsequently passing MUST NOT by itself discard or rewrite that result.
This includes selected success, cancellation and deadline-exceeded results.
Their eligibility remains subject to independent output, authorization,
channel-lifetime and shutdown cutoffs; a failure preventing required result
output terminates the connection rather than silently dropping the result.
Once emission begins, the frame and resulting ciphertext MUST remain immutable.
Changing the local owner or splitting the frame across records/exchanges MUST NOT
create another emission decision, restart its allowance or reset its terminal
state. Continuing
I/O remains subject to expiry, withdrawal, stop and channel-lifetime checks;
those checks may abort, but cannot rewrite or replay the selected output.

Application cancellation remains an encrypted core cancel on U after readiness.
It is distinct from aborting a poll or socket. Core cancellation/deadline
selection can progress while I/O stalls; cancellation cannot overtake accepted
ciphertext, and may be unable to reach the peer before the connection aborts.

### 4.4 Uncertainty, native errors and close

**R13-13 (uncertainty; both roles).** Any canceled, timed-out, truncated, reset,
duplicate or otherwise uncertain open/send/poll/close exchange MUST retire the
whole association, invalidate H, stop admission and dispose of both streams and
traffic state. This applies even when an HTTP library reports a request as
unsent or retryable. Requests, ciphertext, RPCs, notifications, principals and
sessions MUST NOT migrate/replay automatically on a replacement. A later attempt
MUST establish fresh Noise, counters, correlation namespace, current policy and
ready; recovery/subscriptions require independent explicit negotiation. Remote
effects can remain unknown and surviving executions remain accounted.

For a lawful request that can be rejected before body/Noise processing, the
host uses the following bounded, empty-body native responses. No status denotes
a correlated result or discloses credential validity. After irreversible output
or unsafe parser state, aborting TCP/TLS is preferable to attempting a response.

| Host detecting condition | HTTP signal when safe | Initiator observation |
|---|---|---|
| Bad method | 405, `Allow: POST` | Setup/association failure |
| Unknown path or unconfigured authority | 404 | Selection failure |
| Malformed headers, framing, route/counter syntax or state | 400 | Carrier failure; not a precise remote Syntra cause |
| Unsupported HTTP version | 505 | Selection failure |
| Origin rejected | 403 | Admission failure; not Syntra `PERMISSION_DENIED` |
| Header/count bound | 431 | Carrier bound failure |
| Declared body bound | 413 | Carrier bound failure |
| Rate or capacity exhausted | 429 or 503 | Unavailable/admission loss, not a correlated `RESOURCE_EXHAUSTED` result |
| Unknown, expired, retired or unusable H, including duplicate ownership | 410 | Association loss; no lookup sub-reason |
| Handshake, record authentication, core policy or fatal wire failure | Native close, no diagnostic body/status required | Generic loss absent better local evidence |

**R13-14 (error handling; both roles).** Hosts MUST use empty bounded error
responses without diagnostic bodies and retire known affected slots; malformed
H MUST NOT identify a slot by prefix or relaxed decoding. Initiators MUST treat
every unlisted status, informational response, 3xx, 401/407 or malformed success
as terminal for the attempt/association, without following Location,
WWW-Authenticate, Proxy-Authenticate or Retry-After. Locally detected bounds,
deadlines, trust or core errors MUST remain distinguishable locally. A peer's
native error MUST NOT synthesize a host-sent RPC verdict; unfinished calls
normally settle as `UNAVAILABLE`, subject to existing deadline, cancellation,
withdrawal and already-selected terminal precedence.

**R13-15 (close and cleanup; both roles).** Graceful shutdown MUST stop admission,
drain eligible selected output under one absolute grace deadline, and reserve
time for closing both streams. A client may send empty `close` on U after that
drain; the host MUST invalidate H, stop both directions, settle calls once and
attempt 204 within the remaining budget. A pending poll may receive 410 or a
native close. Loss of close/204 MUST NOT trigger retry or imply unsuccessful
effects. Host-initiated close may simply retire the pair after bounded drain.
Security failures may skip drain. Handle invalidation, permit cleanup and
transport-task ownership MUST survive partial shutdown; unfinished external
executions MUST retain their accounting until actually stopped. No tombstone or
retained response may enable resumption. An absent slot is always unusable.

During an R13-15 graceful drain, the role MUST retain the carrier operations
needed to finish eligible selected output, including poll progress for host
output and response processing for client uploads. Stopping application admission
MUST NOT itself cancel one HTTP direction and thereby retire the pair before
drain completes. A drain cutoff, security failure or uncertain exchange still
requires bounded abort of both directions; graceful shutdown does not guarantee
delivery. Local completion and failure reporting follow R13-22.

### 4.5 Limits and timers

**R13-16 (bounds; both roles).** The following wire ceilings and positive local
defaults MUST be enforced before attacker-sized allocation or dispatch. Local
budgets may be shorter/lower within the common contract; implementations MUST
document chosen values. They MUST NOT silently enlarge wire/security ceilings.
All timers use elapsed time including suspend; trickle bytes, empty polls and
phase transitions MUST NOT renew an absolute budget. Unknown elapsed continuity
MUST retire live state. Both directions need independent progress accounting.

| Resource or operation | Proposed ceiling / local default |
|---|---|
| Total endpoint attempt through validated ready | 15 s maximum, including DNS, proxy, both sockets/TLS, open and polls |
| Noise plus encrypted first hello/confirmation | Shared 5 s maximum, from start of M1 processing/emission; no restart for D |
| Header block including start line and final CRLF | 16,384 bytes maximum, 64 fields maximum |
| One start line / one field line including CRLF | 2,048 / 4,096 bytes maximum |
| Header assembly from first header byte | 5 s maximum, also subject to exchange/setup deadline |
| M1 / M2 | Existing context-dependent M1 bound / exactly 48 bytes |
| One send or nonempty poll body | One ciphertext, 17 to 65,535 bytes inclusive |
| Plaintext per record / serialized frame | Existing 65,519 bytes / 1,048,576 bytes ceilings |
| Empty poll request, 204 or native error body | Exactly zero bytes |
| Complete send or open exchange | 5 s default, shortened by setup/frame/call budgets |
| Poll hold / whole poll exchange | 25 s / 30 s maximum; shorter for establishment, output or lifetime expiry |
| First D binding | Within the shared channel establishment deadline |
| Subsequent poll absence | 5 s maximum after last response completes; close slot on expiry |
| One frame's output across all records and HTTP exchanges | 10 s maximum from dequeue for emission, not per send or poll |
| Next authenticated record including idle/partial wait | 60 s default; configurable up to existing 24 h ceiling |
| Partial authenticated frame assembly | 30 s default; configurable up to existing 24 h ceiling |
| Carrier teardown | 2 s default, also within caller's total close deadline and existing ceiling |
| Channel age / protected records per direction | Existing 24 h / `2^32` ceilings |
| HTTP exchanges in flight per association | One on U and one on D; no pipeline or third stream |
| Complete carrier-input slots | One by default; a record held by the driver remains in aggregate byte accounting |
| Per-direction pending operations including active / buffered frames | 64 / 64 defaults, each at most existing 1,024 ceiling |
| Per-association input / output memory | 4 MiB / 4 MiB defaults, counted separately including active buffers and copies |
| Listener logical associations / unauthenticated handshakes | 128 / 32 defaults; two socket permits reserved per association |
| Listener unbound accepted streams | 32 default, with 5 s first-header/association deadline |
| Host-wide input/output memory combined | 256 MiB default, separate from per-association caps |
| Open admission rate | 32/s with burst 32 per listener; 4/s with burst 8 per source by default |
| Active associations per authenticated principal | 16 default; admission is also aggregate-bounded |

The host starts accepted-stream timers even if the peer supplies no first byte.
Initiators start total attempt time before resolution. The core
timer starts at role-local Noise completion and cannot extend either common
establishment deadline. A client exchange's clock starts before its first
request-byte handoff; a host exchange's clock starts with its first received
request byte, with the accepted-stream deadline also covering silence before
initial association. Poll hold starts after the complete empty request, but
header parsing, hold and complete response emission still share that exchange's
absolute deadline. The host leaves time for response emission or aborts; no
new write allowance starts at hold expiry. Header assembly time is contained
within the poll exchange deadline; waiting for a long-poll response header is
not a new budget.
U's idle lifetime is that of the live association, not a fresh request timeout.
TLS/proxy/library allocations and background jobs also need documented finite
aggregate bounds. The two-stream reservation is held through teardown.

Under R13-16, each role MUST preserve the original elapsed-time origin and
remaining allowance across dialing, proxy negotiation, TLS, HTTP, Noise and core
readiness, including both U and D. A layer may shorten an allowance but MUST NOT
replace it with a fresh full budget. Each operation MUST obey the earliest of
its own cutoff and all applicable attempt, outage, output, authorization and
channel-lifetime cutoffs; expired applicable allowance permits no further
protocol I/O. The outage cutoff bounds attempts and locally required recovery,
not I/O on a locally ready active connection, as defined in R13-27.
Receiving complete M1 or transferring it to channel processing MUST NOT restart
the host's open-exchange deadline. If local readiness additionally requires
negotiated recovery after core ready, that negotiation MUST fit within the
remaining attempt and outage allowance; core ready alone does not establish
recovery readiness. Successful local establishment releases its setup and outage
I/O cutoffs, not the retained reconnect accounting or independent active-channel
and operation deadlines. Clocks and generation identities are role-local; peers
need not synchronize them.

Empty polling can demonstrate that HTTP is responsive while an independent
next-record timer expires. There is no indefinite-idle guarantee or new heartbeat.
If authenticated output is pending without a poll, queue/output budgets can
expire earlier than the five-second poll gap. A lower body/frame policy needs
explicit deployment documentation; interoperable HTTP implementations support
the common record ceiling and at least 16 concurrent RPCs, with bounded maximum.

**R13-17 (overload and fairness; host).** The host MUST separately bound source,
association, principal and aggregate admission; lookup/crypto workers; active
and surviving executions; subscriptions; and queued/active input and output in
both items and bytes. Exhausted pre-auth admission MUST refuse before allocation
or expensive work. Lawful excess RPCs MUST follow existing correlated
`RESOURCE_EXHAUSTED` behavior without sacrificing admitted work. Outbound
saturation MUST terminate rather than silently discard selected results;
notification overflow follows the existing generic/recovery-specific contract.
Progress on cancellation, deadlines, revocation and terminal controls MUST NOT
wait indefinitely behind payloads, polls or application handlers.

### 4.6 Trusted application TLS provider, client and host

**R13-18 (provider boundary; both roles).** A TLS stream accepted as HTTPS or
WSS MUST come from a configured trusted provider executing the actual TLS
handshake in the endpoint process's trust boundary. The provider and its
established TLS library are part of the trusted computing base. Its stream and
verification evidence MUST be delivered together through a local ownership
interface tied to that live stream, role, endpoint and policy generation, after
handshake completion. Arbitrary byte streams plus booleans, remote attestations,
headers, caller-supplied certificate strings or unauthenticated “TLS already
verified” flags MUST NOT construct that interface. Unknown/missing evidence
fails closed before M1.

For R13-18, the trusted provider MUST bind each completed verification to the
selected immutable policy generation as well as the live stream. Both HTTPS
streams MUST independently satisfy that generation; verification of U MUST NOT
serve as evidence for D. Evidence from another generation MUST be rejected even
if authority, negotiated parameters and deadline values match. A provider whose
configuration changes between handshakes MUST either retain the selected
still-permitted snapshot for both verifications or fail the whole attempt.
Withdrawal and current-validity checks remain mandatory under R13-02/19/20/21.
This rule requires a verifiable local association, not a particular representation
of policy identity and not a peer-supplied assertion.

The application may supply the provider and certificate configuration; this is
actual in-process host TLS termination. It is distinct from an untrusted caller
passing a plaintext stream from an external terminator. Safe integration cannot
protect against malicious trusted application code that lies or reads secrets.
Separate-process reverse proxies, service-mesh TLS termination, forwarded claims
and private-network trust remain insufficient for HTTPS/WSS identity. Byte-level
L4 tunnels to the actual endpoint provider are permitted.

**R13-19 (TLS client; initiator/provider).** Before M1, the trusted client
provider MUST verify TLS 1.3 or higher with established secure suites, full chain
to system or explicit configured roots, intended hostname/IP SAN, validity and
documented expiry/revocation policy. SNI and hostname verification MUST use the
selected descriptor, never the proxy or a redirect; IP literals use the
corresponding IP verification policy without inventing a DNS SNI. Negotiated
ALPN MUST be `http/1.1` if present; absence is permitted for an explicitly H1
provider. h2/h3 or an unexpected token MUST fail without fallback. The provider
MUST disable early application data and withhold all Syntra HTTP/WS bytes until
handshake completion. TLS verification and the Noise pin MUST both pass;
neither substitutes for the other. Rejected trust MUST require explicit policy
recovery, not retries against the identical rejected configuration.

**R13-20 (TLS server; host/provider).** The trusted host provider MUST terminate
TLS in-process, present the configured intended valid chain, enforce TLS 1.3 or
higher and the H1 ALPN rule, reject/disable TLS early data, and bind the selected
SNI/virtual host and actual local listener to the HTTP authority allowlist before
M1 admission. Client certificates, if locally required, MUST NOT replace hello
policy or merge privileges. HTTPS U and D MUST each satisfy the same origin and
trust policy; a pooled connection or verified U MUST NOT vouch for D's TLS.

**R13-21 (TLS lifecycle and WSS; both roles).** The provider MUST expose owned
bounded read/write/close operations, partial-I/O semantics, cancellation and
verification failure; it MUST NOT replay application bytes on TLS retry,
renegotiation, resumption or stream replacement. TLS tickets may only establish
fresh verified TLS with no early Syntra data and fresh Noise; they restore no
Syntra state. Resumed TLS MUST still satisfy current identity, roots, validity,
revocation, version, ALPN and policy-generation checks; a ticket MUST NOT bypass
those checks. WSS supplied through this provider MUST retain carrier 3,
`/syntra/1.0/ws`, exact `syntra.1.0`, validated RFC 6455/H1 Upgrade, no compression,
and all current WS record/control/admission rules. TLS records MUST NOT become
Noise or frame boundaries. Close-notify, tickets and successful stream flushes
MUST NOT attest application completion. Forwarded metadata MUST remain invalid.

### 4.7 Sockets, reactors and scheduling

**R13-22 (I/O ownership; both roles).** Native dialers/listeners MUST own each
accepted/connected socket, provider stream, association permit and cancellation
registration through bounded shutdown. Nonblocking reads/writes MUST preserve
partial prefixes/headers/bodies and exact ordered output. Reactor readiness is
only permission to attempt I/O, not proof of bytes sent/received; timers and
revocation MUST continue during stalled I/O. Blocking DNS, certificate, store or
policy work MUST use bounded workers and remain accounted after timeout until
it exits. Accepted handshakes MUST be driven concurrently within admission caps,
not serialize all accepts behind one slow peer. A timeout MUST not detach an
unowned writer, poll, lookup or external execution.
Cross-thread task/worker transfer MUST register ownership and a stop path before
handoff. Cancellation requests stop, not task destruction: the connection owner
MUST retain join/completion observation and permits until the task actually exits.
Late callbacks MUST check the association generation before admitting bytes or
completing operations. An incomplete close MUST retain that owner for later
observation without starting another grace budget or reviving the association.

Under R13-22, local shutdown reporting MUST distinguish cleanup completion from
failure of an owned operation. Observing that an operation exited does not prove
that it succeeded. Any aggregate shutdown report MUST preserve every observed
owned-operation failure, including a reconnect-owner failure, even when all
cleanup completes. If a failure count is exposed, it MUST NOT be zero when any
such failure was observed. A summary may report failure categories without
private diagnostic text, but MUST NOT turn a failed child outcome into success.
An incomplete shutdown outcome MUST remain observable; later observation of the
same shutdown may report that no work remains but MUST preserve its observed
failures and distinguish that completion from the earlier incomplete outcome.
This requires bounded outcome accounting, not an unbounded diagnostic history.
Stop/shutdown MUST prevent a replacement attempt even if the last observed
failure would otherwise be retryable. These are local observations, not new wire
statuses or evidence of remote effects.

No reactor, TLS vendor, callback signature or task runtime is a wire identifier.
A reactor integration needs a suspend-inclusive elapsed clock and deadlines,
not just socket readiness callbacks. An embedder supplying streams retains the
same security and shutdown obligations as an implementation-owned dialer.

### 4.8 Standard explicit proxy tunnels

**R13-23 (proxy selection; initiator).** A configured route MUST be direct,
one SOCKS5 CONNECT tunnel, or one HTTP CONNECT tunnel to the selected target
authority. Automatic system/PAC discovery, chained proxies, transparent HTTP
forward mode and fallback to direct or another proxy MUST NOT occur. Each U/D
needs its own tunnel to the same descriptor. DNS/proxy negotiation MUST fit
the original 15-second endpoint attempt and bounded worker/socket quotas. Proxy
credentials MUST be provisioned separately, scoped to the proxy and kept out
of origin requests, Noise credentials, URLs, logs and failover endpoints.
Production transmission of secret proxy authentication MUST require a verified
protected proxy hop; SOCKS username/password and HTTP Basic alone provide no
confidentiality. Trust in the proxy hop MUST NOT replace endpoint TLS or Noise.
If TLS protects the proxy hop, its hostname, trust roots and provider policy
MUST be configured separately from endpoint trust, verified before proxy secrets,
and owned/accounted through the nested tunnel's shutdown. Origin HTTP framing
rules do not override CONNECT's special tunnel-response rules below.

**R13-24 (SOCKS5; initiator).** SOCKS support MUST implement RFC 1928 version 5
CONNECT, exact reply framing and bounded IPv4, IPv6 and domain-address parsing.
Only explicitly configured no-auth or RFC 1929 username/password methods may
be offered; the selected method MUST have been offered. Unsupported method,
version, reserved byte, address type, nonzero reply or failed authentication
MUST close the tunnel without origin data or automatic downgrade. RFC 1929
username/password lengths MUST be 1 through 255 bytes. Domain targets are
bounded to SOCKS's 255-byte field; deployments MUST explicitly choose local
resolution with address filtering or remote proxy resolution. That choice MUST
NOT change the intended hostname, Noise pin or scope. BIND and UDP ASSOCIATE
are not supported by this proposal.

**R13-25 (HTTP CONNECT; initiator).** CONNECT MUST follow RFC 9110 §9.3.6 using
authority-form `host:port` with IPv6 brackets and matching Host, with bounded
HTTP/1.1 header parsing under the table's byte/count/assembly limits. Any valid
2xx establishes the byte tunnel at the end of the header block; per the standard,
Content-Length/Transfer-Encoding on that successful CONNECT response MUST be
ignored, not used to consume tunnel bytes. Read-ahead bytes MUST be preserved
for endpoint TLS or HTTP. Non-2xx, malformed framing, 407 or redirect MUST fail
the attempt without automatic challenge/retry or origin bytes. Optional
preconfigured proxy Basic authentication follows RFC 7617 and the protected-hop
rule; challenges cannot acquire or forward Syntra credentials.

After a tunnel succeeds, endpoint HTTPS TLS or WSS TLS/Upgrade precedes Noise;
HTTP without TLS still requires Noise. The proxy never authenticates the Syntra
host/principal. Listener support means accepting origin streams, not exposing
an open forward proxy. Host routing policy rejects unconfigured authorities;
client address policy and controlled proxy egress bound SSRF/DNS-rebinding risk.

Absolute-form HTTP forwarding is outside this proposal, including when the
forward route is explicitly configured. Supporting it would require a separate
reviewed mapping for request targets, proxy-hop credentials, fixed U/D ownership
and end-to-end framing; it cannot be inferred from CONNECT support. Automatic
cross-carrier failover likewise remains prohibited by R13-01/26. Neither local
configuration nor a successful connection creates an exception to these rules.

### 4.9 Endpoint failover, backoff and forwarding control

**R13-26 (endpoint failover; initiator).** Failover MUST use a finite explicitly
provisioned ordered set of endpoint descriptors, each with its own allowed
authority, route and TLS policy and an independently authorized pin/scope/binding
tuple. All descriptors in an automatic failover set MUST select the same carrier
binding. No endpoint is learned from DNS answers, Location, Alt-Svc or HTTP errors.
Both streams MUST stay on one selected descriptor; no cross-origin association,
credential/header forwarding, connection coalescing or carrier guessing is
permitted. Changing endpoint MUST retire the whole prior attempt, generation-
fence its callbacks and create fresh Noise/current authentication. Automatic
failover is permitted only for transient availability failure under explicit
application policy. Detected trust, protocol, credential or authorization
rejection MUST block that policy generation until explicit recovery, even if
other endpoints are available. A generic close is only loss, not an inferred
credential verdict. The new attempt MUST obtain its hello credential through an
application provider explicitly scoped to the selected descriptor; it MUST NOT
copy a prior hello or forward a credential merely because an endpoint failed.
Unfinished RPCs MUST NOT transfer to a successor. Each descriptor's route remains
fixed; endpoint selection does not enable hidden per-route proxy fallback.

For R13-26, route selection MUST finish before the endpoint-scoped credential
decision. That decision MUST be supplied the selected descriptor and policy
generation, and MUST authorize release of the explicit hello credential to that
descriptor. Two descriptors may use the same credential only when provisioning
independently authorizes both; sharing a provider, hostname, pin or failover set
MUST NOT imply that permission. An obsolete or withdrawn selection MUST NOT
release credentials or complete into a successor attempt. Each attempt MUST
retain the original attempt/outage cutoffs defined by R13-16/27.

**R13-27 (backoff; initiator).** Reconnection MUST be opt-in, single-owner and
bounded in attempts and total elapsed outage, including DNS, both streams,
proxy/TLS, handshakes, cleanup, waits and paused time. The proposed local default
is at most five attempts including the first within 120 seconds, with full
jitter uniformly in `[0, min(30 s, 250 ms * 2^k)]` before retry k (k=0 for the
first retry). The outage clock starts before the first attempt. Implementations
MUST cap arithmetic, schedule at least a one-millisecond timer delay when a
jitter sample is shorter, and not accumulate attempts on wake. Endpoint rotation
MUST NOT reset the attempt count or outage origin. Exhaustion without a locally
ready active connection MUST leave a stopped state requiring explicit restart;
valid ready alone MUST NOT reset the outage budget. The default reset criterion
is 30 seconds of continuous locally ready active operation. A local lower budget
is permitted and documented; Retry-After MUST NOT extend it. Reconnect MUST never
imply RPC replay or recovery readiness.

For R13-27, local readiness requires validated core ready and, when configured as
a prerequisite to application admission, successful fresh recovery negotiation.
The continuous-active reset interval starts only at that local readiness event,
not at M2, core ready alone when recovery is required, or an empty poll response.
The attempt and outage cutoffs apply through local readiness. After that event,
expiry of the retained outage allowance MUST NOT alone terminate the live
association or prohibit its ordinary I/O. Before the reset criterion is met,
attempt count and elapsed outage remain retained; loss or pause MUST use those
original values to decide whether another attempt is permitted. For example, a
connection becoming locally ready at outage second 110 may remain active past
second 120 and reset after 30 continuous active seconds; loss before that reset
and after second 120 leaves it stopped without another attempt. Loss before
local readiness, including stalled required recovery, remains subject to the
original cutoff. Meeting the reset criterion starts a new accounting interval
only on a subsequent outage; it does not renew channel lifetime or authority.

**R13-28 (pause/resume; both roles).** Forwarding pause MUST stop new application
admission and dialing, fence the active generation, retire any live/establishing
association and settle callers once. Accepted output may only drain within an
explicit bounded stop budget if security/lifetime still permits; otherwise it
aborts. Pausing MUST NOT freeze cipher state, defer nonce/lifetime/revocation
checks, buffer unbounded work or suspend an active poll indefinitely. Resume
MUST start a fresh attempt only on explicit application action and with
remaining attempt/outage budget; it MUST NOT reuse H, sockets, ciphertext,
principal or subscriptions. Repeated resume while already running MUST NOT
spawn another dialer. Old callbacks MUST NOT deliver into the resumed generation.

On a host, pausing forwarding means stopping new admission and retiring the
affected associations under the same bounded ownership rule; resuming permits
new associations only. Merely suppressing handler execution while preserving
a live authenticated channel is not the forwarding-pause operation defined here.
Offline/suspend/network-change hints confer no reachability or trust. Explicit
restart after exhaustion is distinct from resume and cannot silently clear a
trust-policy block or replay prior work.

Under R13-28, pause requests from independent control scopes MUST remain
independent: forwarding resumes only after every applicable pause is explicitly
cleared and all stop, policy and budget gates permit a fresh attempt. A network
availability or wake notification MUST NOT clear an application pause. Repeated
pause/resume notifications MUST NOT reset outage accounting or erase an observed
shutdown failure.

### 4.10 Composition boundaries and lifecycle obligations

**R13-29 (credentials and diagnostics; both roles).** Root credentials MUST
remain exclusively inside encrypted hello or explicitly allowed post-active
RPC payloads. AKs MUST enter only standard Noise PSK input. Implementations MUST
redact H, enrollment handles, proxy secrets, credentials, payloads, keys, raw
headers/bodies and private provider/store errors from ordinary logs, traces,
metrics and HTTP access logs. Error/status text MUST remain generic. Rotation,
current validity/revocation and same-principal checks MUST remain host-owned;
default method/subscription authorization MUST deny. Record authentication and
HTTP success MUST NOT renew authority or imply exactly-once effects.

The following table summarizes the proposed composition contracts. Requirement
IDs identify the obligations above; this summary adds no language-specific
interfaces, packaging requirements or permission to ship draft behavior.

| Boundary | Technical contract | Requirement trace |
|---|---|---|
| Channel establishment and records | Canonical context, fresh Noise, strict encrypted hello, bounded frame assembly, ordered records and terminal failure behavior remain common across carriers | R13-01, R13-05, R13-06, R13-09, R13-11, R13-16 |
| Carrier admission | A complete bounded input-slot commitment may be acknowledged independently of decryption; authentication precedes plaintext use and dispatch | R13-07, R13-09 |
| Output selection | One complete selected frame passes the emission gate once, then finishes in order or aborts under its original deadlines; no fragment re-gating or ciphertext replay | R13-12, R13-13 |
| Streams, admission and shutdown | U/D ownership, permits and completion observation survive handoff and incomplete shutdown; cleanup completion and operation failure remain distinct | R13-08, R13-15, R13-17, R13-22 |
| TLS and WSS | Each stream has actual trusted in-process verification tied to its role, endpoint and policy generation; WSS retains its exact endpoint, Upgrade, subprotocol and channel requirements | R13-18, R13-19, R13-20, R13-21 |
| Endpoint replacement | One opted-in bounded owner selects independently provisioned same-carrier descriptors, obtains endpoint-scoped credentials and establishes fresh state; pause/outage accounting and no-replay rules persist | R13-26, R13-27, R13-28 |
| Authorization and recovery | Carrier selection never expands enrollment permissions or grants a principal; current host policy remains authoritative, and later connections require explicit recovery and subscription restoration | R13-01, R13-07, R13-13, R13-29 |

External execution leases, active provider jobs and incomplete shutdown owners
remain alive/accounted independently of the transport handle's apparent close.
An interface carrying plaintext frames alone is not a complete protected
connection; it also needs the selected carrier's establishment, encryption,
ordering and lifecycle obligations. This fixed H1/two-stream mapping makes no
browser support claim: a platform unable to enforce these controls needs a
separately reviewed feasible mapping and execution evidence. Local interfaces,
component separation and build options define neither another wire protocol nor
an optional encryption mode.

## 5. Alternatives considered

1. **Do nothing.** Keeps the three-carrier surface small but does not satisfy
   environments requiring ordinary HTTP request traffic or application TLS
   providers.
2. **One RPC per HTTP exchange with header credentials.** Rejected because it
   removes the shared Noise/hello/session contract, needs another authentication
   mapping and cannot carry notifications/cancellation as the same ordered peer.
3. **Bidirectional streaming bodies, H2/H3 or extended CONNECT.** Could reduce
   request overhead but requires additional framing, flow-control and platform
   contracts. Not part of this bounded H1 proposal; no silent ALPN substitution.
4. **Arbitrary pooled requests plus retransmission/deduplication.** Requires
   authenticated ordering, retained responses, acknowledgment and nonce-safe
   replay rules. Fixed streams and retirement on uncertainty deliberately avoid
   that state machine. Reconnect availability is lower, but uncertainty is explicit.
5. **External TLS terminator or caller “verified” flag.** Rejected as endpoint
   proof. The in-process provider performs actual TLS and is explicitly trusted;
   forwarded claims remain untrusted.

## 6. Compatibility

The proposed HTTP bindings add two context values and endpoints; existing
TCP/WS/WSS bytes, Noise patterns, common records, IDL and recovery encoding do
not change. An unmodified peer rejects 4/5 rather than interpreting them as
another carrier. Carrier selection remains explicit configuration, never hello,
HTTP status or ALPN negotiation. The permitted-binding set does not expand merely
because software supports more variants.

The proposed TLS-provider boundary changes the meaning of acceptable local
direct-host evidence for HTTPS/WSS. It requires explicit security review of
the current prohibition on caller-terminated WSS streams. The fixed H1 mapping
does not reuse per-exchange credential/session semantics from another mapping.
No existing field, tag or reserved byte is repurposed and no dual-format fallback
is introduced.

The target is additive pre-release work, but this is not a compatibility verdict.
Maintainers need to classify carrier additions, enrollment-policy persistence
and the TLS trust-boundary change against accepted decisions as well as current
owners. If deemed wire-incompatible, governance's major-version RFC requirement
blocks activation under Syntra 1.0. Candidate generation and downstream pinning
wait for that disposition. This proposal neither changes a baseline nor grants
release compatibility by passing Buf.

## 7. Security considerations

The trust path is network/proxy to optional verified endpoint TLS, bounded HTTP,
bound stream association, Noise record authentication, bounded frame validation,
fresh hello/current credential policy, then method authorization. HTTP routing
and TLS metadata never jump to the principal boundary.

| Threat | Proposed mitigation / residual exposure |
|---|---|
| Handle guessing, leakage, fixation or first-poll race | Independent random H, atomic one-time D binding, no URL/log/cookie carriage, bounded admission and no resumption. A leaked H can cause denial of service, never authenticated effects; HTTP reveals it to observers |
| Cross-origin leakage, SSRF or credential forwarding | Provisioned descriptors only, exact authorities/paths, configured DNS/address/proxy-egress policy, no redirects, no coalescing, no ambient credentials |
| HTTP smuggling, body transform, caching or library retry | One CL, strict H1 parsing, bounded full body, no TE/compression/pipeline; disable middleware retry/cache; uncertain delivery kills the pair |
| Record loss/reorder, nonce reuse or replay | One exchange in flight per direction, implicit authenticated order, exact immutable output or abort, no redelivery/new-channel replay |
| TLS impersonation or provider substitution | Actual trusted in-process TLS, stream-bound local evidence, chain/name/version/early-data/ALPN checks independently of Noise; forwarded claims invalid |
| Poll/slowloris/handshake exhaustion | Header/body/deadline caps, reserved pair/slot quotas, unbound pool, hold/gap limits, worker and per-principal/aggregate memory/execution accounting |
| Replayed M1 or HTTP 201 mistaken for identity | Fresh responder keys and client confirmation, complete strict encrypted hello, host-owned current enrollment and root identity before ready |
| Pause/wake, stale callbacks or detached tasks | Retire generation, suspend-inclusive absolute time, no stored traffic state, owned incomplete shutdown and surviving execution quotas |
| Proxy secret exposure / endpoint confusion | Separate proxy credentials on verified protected hop; standard tunnels, no fallback; target SNI/pins/scope independent of proxy |
| False success from 204, flush, FIN or TLS close | Native carrier signals never complete RPCs; selected core terminal outcomes and effect uncertainty remain separate |

Unencrypted HTTP intentionally lacks outer traffic-metadata confidentiality and
allows on-path disruption, as encrypted raw TCP does. This is a production policy
choice only with integral Noise and explicit enrollment/carrier permission;
it does not authorize WS outside loopback. TLS-provider compromise and host
compromise are within endpoint compromise, not solved by additional headers.
TLS, Noise and routing handles provide no application deduplication, durable
checkpoint or independent authorization system.

## 8. Test plan and acceptance criteria

All rows below are **proposed runtime tests, NOT_EXECUTED**. Their isolated machine
definitions and static fixtures are in the [candidate bundle](0013-http-tls/README.md).
Labels are local review references, not registered CONF cases. Every scenario needs separate
client and server evidence, exact revisions, parameters, observable bytes/events,
and failure/no-dispatch assertions. Activation work assigns accepted requirement
IDs and registers role-specific manifests/fixtures under the conformance guide.

| Proposed test | Requirement trace | Required observations, including negatives |
|---|---|---|
| R13-T01 | R13-01 | Context 4/5 encoding through canonical encoder; mismatched carrier/mode/scope/selector rejected before lookup; no default binding or fallback; existing 1/2/3 bytes unchanged |
| R13-T02 | R13-02, R13-04 | Exact authorities/path/method/Origin; userinfo/query/fragment, redirects, Alt-Svc, cross-origin handles and cookies/auth rejected; immutable selected generation retained or retired on withdrawal without freezing current validity; zero leaked secrets or second target |
| R13-T03 | R13-03, R13-16 | Header/body limits at MAX/MAX+1; conflicting/duplicate CL, TE+CL, obs-fold, malformed lengths, chunked/compressed/extra units and pipelines fail closed; split every header/body boundary, bounded read-ahead |
| R13-T04 | R13-05, R13-06 | Fresh M1/M2, invalid pin/M2, lost 201, CSPRNG error/collision exhaustion, context replay; no hello after failure, no principal/effects from M1, no leaked slot/socket permit |
| R13-T05 | R13-07, R13-08 | Unknown/leaked H, first-poll race, two D binders, wrong U/D/authority/owner/H, restart and abandoned open; one binding, bounded lookup, no identity/resumption, cleanup deadlines |
| R13-T06 | R13-09, R13-10, R13-11 | 204 follows full bounded carrier-input admission without awaiting driver decryption; no plaintext dispatch before authentication; blocked driver/full queue/retired-slot races; hello/ready fragmentation, 16 concurrent RPCs, notifications/cancel, counter faults and empty poll with no nonce/auth progress |
| R13-T07 | R13-12, R13-13 | Fault at every request/response write/read split, dropped send acknowledgment, canceled poll, duplicate library send, invalid AEAD, accepted frame spanning many polls; expired unsent request skipped before nonce use, live request timeout encoded once, host-selected success/cancellation/deadline results preserved across call-deadline expiry; retire once, no re-encryption/re-gating/replay or new-generation delivery |
| R13-T08 | R13-14, R13-15 | Every native error/status and malformed success, EOF/RST/Connection-close, failed close response; no fabricated RpcResult, terminal precedence, bounded drain/teardown with required U/D progress retained, retained incomplete owner/external leases |
| R13-T09 | R13-16, R13-17 | Controlled elapsed clock for poll hold/gap, handshake, output, record/frame, age, outage and suspend; no phase/handoff/recovery budget reset or I/O after applicable cutoff; setup/outage I/O gates end only at local readiness; trickle/204 never renew; byte/item/source/principal/global caps; handler stall does not starve timers/cancel/revocation |
| R13-T10 | R13-18, R13-19, R13-20, R13-21 | Separate real client/server provider evidence for WSS (3) and HTTPS (5): both cover chain/name/SNI/expiry/revocation rejection, TLS 1.2/early-data/h2 failure, explicit-H1 absent-ALPN success, missing/mismatched/fabricated evidence, selected-policy withdrawal, ticket with fresh Noise and forwarded-claim rejection; only HTTPS covers wrong D identity/generation, equal-authority/deadline mixed generations and policy replacement between U/D handshakes |
| R13-T11 | R13-22 | Partial nonblocking I/O, spurious readiness, concurrent accepts, stuck DNS/root/store workers, close timeout; workers/permits remain owned until completion, no detached writer; completed cleanup preserves owned-operation failures in aggregate reports, incomplete outcomes remain observable, stop prevents replacement |
| R13-T12 | R13-23, R13-24, R13-25 | Real independent SOCKS5/CONNECT peers: IPv4/IPv6/domain, selected method, RFC 1929/Basic protected hop, all rejection/truncation cases, CONNECT 2xx read-ahead and ignored CL/TE; no unprotected proxy secret, absolute-form forward route, automatic challenge/direct fallback/secret forwarding |
| R13-T13 | R13-26, R13-27, R13-28 | Finite same-carrier rotation with selected-descriptor/generation credential decisions, one dialer, jitter/arithmetic bounds, five-attempt/120-second defaults, ready/loss cycles before active reset, late local readiness with live I/O past outage cutoff but no replacement after loss, required-recovery-gated reset, pause through outage expiry, independent pause scopes and network hints, explicit resume/restart, trust block and stale callbacks; no carried RPC/subscription/cipher state |
| R13-T14 | R13-07, R13-17, R13-29 | Host-owned empty-credential policy, same-principal mismatch, expiry/revocation while poll/write idle, default deny, overload isolation and secret-log/access-log scanning; no protected delivery after cutoff |

Acceptance evidence still required:

- [ ] Public protocol/security review resolving §10, including handle-race/HTTP
  uncertainty and trusted-provider trust-boundary analysis.
- [ ] Compatibility/version decision and collision-free authoritative allocations.
- [ ] Active-maintainer acceptance with reviewed revision and public approval
  evidence; disclose author/self-approval if applicable.
- [ ] Synchronized owner requirements, registered cases and fixtures after acceptance.
- [ ] Independent HTTP/HTTPS wire peer or independent packet-fixture verification;
  local round trips alone are insufficient.
- [ ] Fault-injection execution at native HTTP, TLS-provider, proxy, reconnect,
  ownership and persistence boundaries; real TLS negative tests, not booleans.
- [ ] Focused codec/runtime/native checks; ABI capability/shutdown checks if
  exposed. Browser/device support requires its own feasible contract and execution.
- [ ] Existing repository, schema and regression checks; no fixture-baseline reset.

Repository validation for this proposal uses the documented toolchain:
Python 3.14, PyYAML 6.0.3 and Buf 1.59.0. These are static/tooling checks and do
not execute any R13-T scenario or grant normative approval:

```sh
python3 scripts/validate-repo.py all
python3 scripts/validate-schema.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

Actual command results belong in the review report, bound to the base revision
and this uncommitted draft. Formal conformance remains NOT_EXECUTED.

## 9. Drawbacks and risks

Two persistent H1 sockets, one record per POST/response and sequential polling
increase latency and connection count. Large frames can require many exchanges
within ten seconds; high-latency deployments may not meet that output budget.
The mapping intentionally closes on any ambiguous exchange instead of solving
HTTP retransmission with an additional acknowledgment protocol.

Long polls require operational idle-timeout configuration and cannot pass
through TLS-terminating intermediaries under this endpoint trust model. Pair
routing complicates multi-host deployments; process loss requires fresh Noise
and explicit recovery. Trusted provider integration expands the trusted
computing base and needs independent review. Browser APIs cannot promise the
fixed H1 stream-pair controls described here. Local unit tests cannot establish
those deployment or security properties.

## 10. Unresolved questions and blockers

1. **TBD — blocker: public acceptance record.** The user confirmed “Approve as
   maintainer” as oscarlaw, the sole listed active maintainer, with self-approval
   disclosed. [Decision 0003](../docs/decisions/0003-http-tls-consent.md) records
   that consent and its limits. It supplies no public RFC/PR approval link or
   reviewed candidate commit. Governance §3 requires public approval; this draft
   cannot manufacture it. Material corrections, including the carrier-input
   acknowledgment rule, need review of the resulting exact content.
2. **TBD — blocker: human security review.** The
   [advisory review](0013-http-tls/review.md) records AI analysis and corrections;
   it is not a human review or an approval vote. Assign human reviewers for HTTP without
   outer TLS, H association/first-poll denial of service, native parser/retry
   controls, resource limits, proxy trust and the in-process TLS-provider boundary.
   The proposed numbers and failure rules are concrete review inputs, not approved
   security parameters. Exploitable findings follow the private security process.
3. **TBD — blocker: compatibility and authority.** Record whether all proposed
   changes are admissible as Syntra 1.0 additive pre-release work under accepted
   decisions. Resolve conflicts through governance, not implementation choices.
   Recheck bytes 4/5 against concurrent proposals; assign authoritative bindings
   only through acceptance and owner synchronization. No registry reservation is
   made by this draft.
4. **TBD — blocker: execution and independent evidence.** R13-T01 through
   R13-T14 now have isolated machine definitions and static fixture checks, not
   runtime verdicts. Activation needs registered, reviewable role/case coverage
   and recorded execution at the real carrier/provider/proxy
   and persistence boundaries. Formal conformance, independent interoperability,
   device validation and security verdicts are not supplied by this edit.
5. **TBD — blocker: activation, freeze and release.** After acceptance, land
   synchronized reference/registry/fixture/candidate changes, then review
   downstream implementation and immutable Git-blob pins. Specification freeze
   and release authorization require separate public decisions and the evidence
   in governance/release policy. Neither gate is cleared by drafting this RFC.

## Appendix: References

- [Contributing](../CONTRIBUTING.md), [governance](../GOVERNANCE.md),
  [maintainer roster](../MAINTAINERS.md), [RFC template](template.md),
  [release policy](../RELEASE.md), [security reporting](../SECURITY.md).
- [Transport and canonical context](../specifications/transports.md),
  [security and authorization](../specifications/security.md),
  [connection lifecycle](../specifications/connection.md),
  [RPC output and outcomes](../specifications/rpc.md),
  [wire validation](../specifications/wire-format.md),
  [recovery](../specifications/recovery.md), [IDL](../proto/syntra/v1/).
- [Conformance guide](../conformance/README.md),
  [carrier registry](../conformance/profiles.yaml),
  [candidate input](../compatibility/syntra-1.0.json),
  [schema tooling and dependency pins](../docs/schema-tooling.md).
- [RFC 9110, HTTP semantics and CONNECT](https://www.rfc-editor.org/rfc/rfc9110.html),
  [RFC 9112, HTTP/1.1](https://www.rfc-editor.org/rfc/rfc9112.html),
  [RFC 6455, WebSocket](https://www.rfc-editor.org/rfc/rfc6455.html),
  [RFC 8446, TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html),
  [RFC 9525, service identity](https://www.rfc-editor.org/rfc/rfc9525.html).
- [RFC 1928, SOCKS5](https://www.rfc-editor.org/rfc/rfc1928.html),
  [RFC 1929, SOCKS username/password](https://www.rfc-editor.org/rfc/rfc1929.html),
  [RFC 7617, HTTP Basic](https://www.rfc-editor.org/rfc/rfc7617.html).
