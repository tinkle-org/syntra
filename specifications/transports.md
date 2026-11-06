# Syntra 1.0 — Transports

Syntra carries encrypted, length-prefixed protobuf frames over TCP, WS or WSS.
Every connection uses Noise followed by encrypted hello, host authentication
and ready. WSS first establishes verified TLS and a WebSocket Upgrade; WS first
establishes an Upgrade and is restricted to loopback development.

This page defines carrier selection, exact context and framing bytes, admission,
resource limits and transport failures. [Security](security.md) defines channel
cryptography and authorization; [connection](connection.md) defines hello/ready
and connection states; [wire format](wire-format.md) defines protobuf validation;
[RPC](rpc.md) defines call outcomes; [recovery](recovery.md) defines explicit
update recovery. BCP 14 keywords are normative.

## 1. Protocol and carrier selection

Syntra 1.0 is one protocol with three technical carrier bindings:

| Carrier byte | Carrier | Outer delimiting | Permitted deployment |
|---:|---|---|---|
| 1 | Encrypted raw TCP | `u16BE(length) \|\| message` for M1, M2 and each ciphertext | Production, with provisioned Noise pin and full host authorization |
| 2 | WS over RFC 6455 / HTTP/1.1 Upgrade | One reassembled binary message per M1, M2 or ciphertext | Explicit loopback development only; no outer TLS |
| 3 | WSS over verified TLS ≥1.3 / RFC 6455 / HTTP/1.1 | Same binary-message mapping | Production; host terminates TLS directly and Noise pin is independent |

All three carriers require the same Noise establishment, record protection
and host authorization. Carrier configuration MUST be explicit and
deny-by-default: an empty/default permitted-binding set enables nothing and
is invalid for an enabled listener or enrollment service. Registering one
binding MUST NOT register another or make credentials portable between them.
The host MUST check the configured carrier, mode, server-key selector and
scope before credential lookup; enrollment admission also applies the
[permitted-binding policy](security.md#4-device-authorization-and-host-lifecycle).
WS registration additionally requires explicit development opt-in and verified
loopback confinement. Carrier selection is configured, not negotiated.

Only the three listed carriers are supported. No standard TCP port or raw-TCP
TLS/ALPN wrapper is defined. HTTP is used only for the WebSocket Upgrade.

**SNTR-SCW-001** — WS/WSS peers MUST use exactly `/syntra/1.0/ws` and the exact,
case-sensitive subprotocol `syntra.1.0`. Selection failures fail closed without
automatic retry as another format, mode or carrier. Every listener MUST require
an explicit valid permitted-binding set matching the selected carrier before
handshake admission. Context or endpoint selection cannot enable a binding.

**SNTR-TCP-001**, **SNTR-WS-004**, **SNTR-WSS-004** — Endpoints MUST explicitly
identify their supported bindings. All use the handshake and record bytes below;
loopback WS support does not permit public traffic.

## 2. Canonical context

**SNTR-SCW-002** — Both roles MUST encode/authenticate this public context `P`
byte-for-byte as the entire Noise prologue and exact clear prefix of M1. No
extra domain, revision, hash, padding, optional field or terminator is present.
Malformed/mismatched context MUST be rejected before credential lookup,
protected dispatch or effects.

Let `S` be the UTF-8 byte length of scope. Offsets are zero-based, half-open.

| Offset | Bytes | Field | Encoding |
|---|---:|---|---|
| `[0,10)` | 10 | domain | Exact ASCII `syntra.1.0` (`73 79 6e 74 72 61 2e 31 2e 30`) |
| `[10,11)` | 1 | mode | `u8`: bootstrap 1, returning 2 |
| `[11,12)` | 1 | carrier | `u8`: TCP 1, WS 2, WSS 3 |
| `[12,16)` | 4 | server-key selector | `u32BE`; zero permitted |
| `[16,24)` | 8 | enrollment epoch | `u64BE` |
| `[24,32)` | 8 | enrollment handle | Eight opaque bytes |
| `[32,34)` | 2 | scope byte length S | `u16BE` |
| `[34,34+S)` | S | intended endpoint/service scope | Exact valid UTF-8, 1–255 bytes, no normalization |

`len(P) = 34 + S`, hence **35–289 bytes**, and `prologue = P`.
Scope is provisioned identity context, not a value inferred/normalized from a
peer URL. Server-key selector, carrier and scope MUST match responder
configuration; a selector cannot create a trusted key. Bootstrap requires mode
1, zero epoch, all-zero handle and no AK. Returning requires mode 2, nonzero
epoch and independent nonzero handle, with a separately provisioned nonzero
uniformly random 32-byte AK supplied only to standard Noise `psk0`.

## 3. Handshake and common records

**SNTR-SCW-003** — The only modes are
`Noise_NK_25519_ChaChaPoly_SHA256` bootstrap and
`Noise_NKpsk0_25519_ChaChaPoly_SHA256` returning, with fresh ephemeral pairs and
empty payloads in both flights.

| Unit | Bytes before carrier framing |
|---|---|
| M1 | `P || 48 Noise bytes`: `82 + S`, or 83–337 bytes |
| M2 | Exactly 48 Noise bytes |
| Both flights | 131–385 bytes; TCP adds two two-byte prefixes, totaling 135–389 bytes |

Unexpected lengths, payloads, modes, carriers, context or trailing bytes MUST
terminate the connection. These flights do not include carrier setup, fresh
client confirmation, hello/ready, enrollment, retries or application recovery.

**SNTR-SCW-004** — The initiator MUST use its provisioned server static key for
Noise authentication and verify M2 before encrypted hello. WSS additionally
requires independent TLS ≥1.3 certificate/hostname verification before M1.
Either trust failure terminates without credential release or fallback.

**SNTR-SCW-009** — After `Split()`, directions MUST have independent standard
Noise transport state, implicit ordered nonces and empty AD. Plaintext is
**1–65,519 bytes**; ciphertext is **17–65,535 bytes**, including the 16-byte tag.
Empty plaintext records are not heartbeats or close markers. Outer lengths and
WS boundaries are not authenticated AD; tampering can cause only bounded
waiting/failure, never unchecked allocation or resynchronization.

**SNTR-SCW-010** — Authenticated plaintext MUST be the byte stream
`u32BE(F) || Frame || u32BE(F) || Frame ...`, where F counts exactly the
serialized `Frame` bytes, **1–1,048,576** inclusive. Tags, varints, wrappers,
unknown fields, method and payload all count; the encrypted four-byte prefix,
record tag and carrier overhead are separate. A deployment MAY lower but MUST
NOT silently raise the frame ceiling. Prefixes/frames may span records;
records may hold multiple complete frames after the initial hello rule.
Authenticate a whole record before using plaintext, enforce F before allocation
and dispatch only complete validated frames. Never decode a partial frame or
scan for a plausible replacement boundary.

**SNTR-SCW-011** — The first client authenticated plaintext MUST start with
exactly one complete framed `ClientHello`. It MAY span records; its completing
record MUST end exactly at the hello boundary, with no complete or partial
trailing envelope. The 1 MiB and frame-assembly budgets still apply. The host
validates hello/current enrollment/root identity/same-principal policy before
ready or protected effects; method policy remains required. A replayed M1,
unauthenticated input or record without a complete valid admitted hello cannot
bind authority or release sensitive output. The host sends ready, not hello.
Violation closes natively and dispatches nothing.

## 4. Encrypted TCP

**SNTR-TCP-002** — The initiator active-opens and the host accepts. Each
accepted socket carries exactly one protected handshake-to-teardown connection;
connections MUST NOT be multiplexed into or shared across sockets.

**SNTR-TCP-003**, **SNTR-TCP-004**, **SNTR-SCW-008** — Carrier 1 MUST encode
every M1, M2 and ciphertext record as:

```text
u16BE(message_length) || message_bytes
```

The length excludes its two bytes. TCP packet/write boundaries have no meaning.
The first bytes are the bounded M1 length, not a clear `u32BE` hello length.
Following establishment, ciphertext carries the encrypted inner u32 stream in
§3. Carrier 1 authenticates the provisioned Noise key and has no outer TLS.
Wrapping a stream externally does not establish carrier 3 identity.

**SNTR-TCP-005** — Readers MUST bound M1 to 83–337 bytes, M2 to exactly 48 and
subsequent ciphertext to 17–65,535 before allocation. Zero or oversized outer
lengths terminate immediately without correlation or a fabricated result.
The independent inner frame ceiling remains §3; no record bound expands it.

**SNTR-TCP-006** — Readers MUST handle partial prefixes/bodies and coalesced
units. Read exactly the declared count, treating the next byte as the next
prefix. Short counts do not permit scanning; long counts wait only within
absolute budgets. Partial prefix/body at EOF is truncated and discarded.
Even EOF at a complete boundary is transport loss, not authenticated success.

**SNTR-TCP-007** — TCP establishment MUST be followed by bounded M1/M2,
verified M2 before client hello, strict encrypted first hello, host policy and
one ready. A new socket never starts directly with a clear hello or resumes an
old cipher/principal/session.

**SNTR-TCP-008** — Public TCP MUST require the same Noise pin, record security,
fresh confirmation and host authorization as other permitted carriers. Bare
plaintext TCP MUST NOT be selected as Syntra 1.0 or auto-fallback. The provisioned
scope/pin and absence of outer TLS MUST be documented.

**SNTR-TCP-009**, **SNTR-TCP-010** — Graceful close follows
[connection](connection.md#5-shutdown-output-and-liveness), then bounded socket
shutdown. FIN/half-close/RST is not a Syntra cancel, completion, truncation
marker or delivery acknowledgment; no half-open connection may remain
indefinitely. Settle unfinished callers as loss, preserve selected outcomes
and discard partial records/frames. Native half-close provides no authorization.

**SNTR-TCP-011** — TCP flow control MUST NOT replace bounded frame, execution,
pending input/output or per-principal limits. Pending write count and byte
bounds MUST be documented; reject/close on saturation per §6, without blocking
cancellation/deadline progress indefinitely.

**SNTR-TCP-012** — OS keepalive MAY be configured but MUST NOT be required for
interoperability. There is no core heartbeat. Per-call deadlines remain
effective; advertised blackhole detection needs documented idle-probe,
matching-response and assembly budgets, not a universal TCP idle guarantee.

**SNTR-TCP-013** — Only byte-preserving intermediaries are compatible. NAT
does not create connection migration; address change/loss requires a new
connection, fresh handshake and explicit recovery. Idle intermediary drops
are abrupt loss. Unbounded buffering or altered bytes violate this binding.

## 5. WS and WSS

### Establishment and admission

**SNTR-WS-001**, **SNTR-WSS-001**, **SNTR-WS-040**, **SNTR-WSS-040** — WS/WSS
MUST use RFC 6455 over HTTP/1.1
Upgrade on TCP, with verified TLS ≥1.3 first for WSS. The sequence is carrier
setup → validated Upgrade → Noise → encrypted hello/current policy → ready.
Each layer completes before the next; no carrier success grants principal
authority. After Upgrade the next data MUST be Noise M1/M2; the six core states
follow [connection](connection.md).

**SNTR-WS-002**, **SNTR-WSS-002** — Peers MUST reject unsupported carrier
mappings. These bindings require RFC 6455 over HTTP/1.1 and the specified Noise
records; no custom TLS or alternate record construction is permitted.

**SNTR-WS-003** — WS MUST be explicitly enabled, loopback-restricted and
disabled by default for production distributions. Validate the configured
loopback target and actual peer confinement; a hostname string alone cannot
authorize a non-loopback resolved peer. Document no outer TLS; Noise remains
mandatory. WS MUST NOT serve public production traffic/credentials.

**SNTR-WSS-003** — Public WSS MUST verify TLS and the independent Noise pin,
with no WS or raw-TCP auto-fallback after either fails.

**SNTR-WS-010**, **SNTR-WSS-010** — The sole canonical path is
`/syntra/1.0/ws`, case-sensitive. WSS uses `wss`
(default port 443 where not otherwise configured); WS uses `ws` only in its
permitted loopback scope. Other paths MUST be rejected.

**SNTR-WS-011** — `ws` and `wss` MUST be explicit and match context carrier
2/3. Scheme or wrapper guessing MUST NOT substitute one for the other.

**SNTR-WS-012**, **SNTR-WSS-011** — The target MUST have no userinfo, query
or fragment. Parameters MUST NOT encode credentials, routing authority or
session handles.

**SNTR-WS-013**, **SNTR-WSS-012**, **SNTR-SCW-006** — Hosts MUST validate
method/version/key/path/subprotocol before 101 and reject `Authorization` and
`Cookie` Upgrade request headers. Initiators send no credentials in the target
or Upgrade. The client MUST validate 101, Upgrade/Connection tokens,
`Sec-WebSocket-Accept` and exact selected subprotocol before any M1; failure
closes without M1. Origin/forwarding headers MUST NOT authenticate or merge
Syntra identity. Upgrade errors contain no Syntra envelope.

**SNTR-WS-014**, **SNTR-WSS-013** — Hosts SHOULD serve the endpoint directly
rather than redirect. A non-101, including 3xx, is not establishment or an RPC
result. Clients MUST NOT automatically change security context or forward
credentials on redirect; any explicit application-selected new target starts
fresh endpoint/carrier verification. WSS → WS downgrade is forbidden.

**SNTR-WS-020**, **SNTR-WSS-020** — Clients MUST offer exactly `syntra.1.0`
and hosts MUST select exactly that case-sensitive token. WSS ALPN, where used,
is `http/1.1` (absence permitted for H1); mismatch fails. Neither token nor
ALPN authorizes a principal or negotiates application capabilities.

**SNTR-WS-021**, **SNTR-WS-022** — Missing or unsupported subprotocol MUST
fail Upgrade without 101 at the host. A client receiving missing/wrong
selection MUST close without M1, reporting local selection failure, never
silently accepting a bare WebSocket or substituted protocol.

**SNTR-WS-023** — Additional offered/selected tokens MUST NOT be interpreted
as fallback, capability, mode or authorization negotiation under this binding.

**SNTR-WS-024**, **SNTR-WSS-021** — The `syntra.1.0` token MUST select the
protected bytes defined here. `Frame.version` is negotiated by hello/ready and
remains 1 for the Syntra 1.0 schema; schema or library revisions do not change
the token or record mapping.

### Binary messages and reassembly

**SNTR-SCW-005**, **SNTR-WS-030**, **SNTR-WSS-030** — One complete reassembled
binary message MUST contain exactly one M1, M2 or ciphertext record. There is
no outer u16 prefix inside WS. A message is not a protobuf envelope: authenticated
plaintext feeds §3's inner framed stream. Text, compressed, empty, truncated
or unauthenticatable messages terminate. WS fragmentation is reassembled by
the carrier; WebSocket frames are neither Noise records nor Syntra `Frame`s.

**SNTR-WS-031**, **SNTR-WS-032** — Syntra data MUST be binary, never text,
including JSON/base64 text. Empty application payloads inside legal encrypted
envelopes remain valid; an empty binary carrier message is forbidden, including
as a keepalive.

**SNTR-WS-033**, **SNTR-WS-034** — Receivers MUST support fragmented binary
messages, including interleaved control frames, with bounded reassembly before
record authentication. No partial fragment/record reaches inner decoding or
handlers. Fragment sizes/FIN are not application processing hints.

**SNTR-WS-035** — Assembled M1/M2/record bounds MUST be enforced during
reassembly before allocating an attacker-declared aggregate: 83–337 / 48 /
17–65,535 bytes respectively. The separate inner frame cap is 1 MiB, not the
carrier-message cap. Exceeding either fails closed without partial dispatch.

**SNTR-WS-036**, **SNTR-WSS-031** — The WS message MUST contain only its
handshake/ciphertext unit, with no TCP u16 prefix or clear u32 frame prefix.
The u32 serialized-frame prefix is inside authenticated encrypted plaintext;
it MUST NOT be omitted merely because WS supplies message boundaries.

**SNTR-WS-041**, **SNTR-WSS-041** — Upgrade/TLS success MUST NOT stand in for
ready, client confirmation or credential validation. No M1 precedes verified
WSS TLS and valid Upgrade; no hello precedes verified M2. The core timer cannot
extend the absolute channel/total attempt budget in §6.

**SNTR-WS-042** — Re-handshake on one WS connection is forbidden. Failure or
second hello requires termination and a new carrier connection.

**SNTR-WS-050**, **SNTR-WSS-050**, **SNTR-WS-051** — Each WS/WSS connection MUST
have one Syntra principal binding from host authentication of encrypted hello
and trusted channel evidence. Upgrade admission MUST NOT establish, replace or
merge it. No parallel HTTP-layer Syntra session exists; `Authorization` and
`Cookie` remain rejected under `SNTR-SCW-006`.

**SNTR-WS-052**, **SNTR-WSS-051** — Credential secrecy MUST follow
[security](security.md); WS is loopback development only, WSS requires verified
TLS in addition to Noise, and neither permits credential logging/echo or release
before channel verification.

### Origin, liveness and close

**SNTR-WS-060**, **SNTR-WSS-060** — Origin MUST NOT be identity, authority or
a substitute for hello/policy. Browser-serving deployments SHOULD use a
documented allowlist as defense in depth, not as channel authentication.

**SNTR-WS-061** — Missing Origin MUST be permitted for native/service clients
unless an explicitly documented browser-only policy rejects it at Upgrade.

**SNTR-WS-062** — Origin rejection MUST precede 101 (HTTP 403), with no Syntra
processing or sensitive disclosure. Document allowlist/accept-all rationale and
log decisions without credential material.

**SNTR-WS-070**, **SNTR-WSS-070** — WS Ping/Pong is carrier liveness, not a
core heartbeat, RPC progress, authorization refresh or durable acknowledgment.
A matching probe response is required to satisfy an outstanding probe. There
is no requirement for a second Syntra heartbeat.

**SNTR-WS-071** — Receivers MUST promptly echo Ping payload in Pong under
RFC 6455, not wait behind handlers, and enforce the 125-byte control limit.

**SNTR-WS-072** — Unsolicited Pong MUST be accepted/ignored but MUST NOT
satisfy an unmatched probe or count as RPC/authentication progress. Probe,
response, idle and assembly policies are bounded/documented; liveness loss
closes with local `UNAVAILABLE` to unfinished calls. No control traffic resets
an absolute channel/record/frame deadline.

**SNTR-WS-073** — Ping/Pong/Close MUST remain carrier controls, never envelopes,
events, client confirmation or terminal results. They do not disturb bounded
fragment reassembly or permit application delivery from partial input.

**SNTR-WS-080**, **SNTR-WSS-080** — Graceful close MUST stop admission, drain
under the absolute [connection](connection.md#5-shutdown-output-and-liveness)
cutoff, then attempt WS Close, WSS TLS shutdown where applicable and TCP close,
all within the remaining budget. Teardown neither acknowledges application
delivery nor rolls back effects.

**SNTR-WS-081**, **SNTR-WSS-081** — Channel/context/framing/authentication and
connection-fatal policy failures MUST terminate natively without a diagnostic
payload or guaranteed WS close code. A received code is not proof of the remote
Syntra error or authenticated orderly completion. RFC 6455 reserved wire codes
1005/1006/1015 MUST NOT be sent; unknown codes never confer Syntra semantics.

**SNTR-WS-082** — A Close during fragmented input MUST discard partial input.
Any Close reply/teardown is bounded; reasons omit credentials/raw input/private
diagnostics. Abrupt loss without Close is `UNAVAILABLE`, not a fabricated result.

**SNTR-WS-090**, **SNTR-WS-091**, **SNTR-WS-092**, **SNTR-WSS-090** — Compression
MUST NOT be offered, negotiated or accepted. Secret/attacker mixed-content
compression and decompression bombs add unnecessary risk; no opt-in compression
mode is defined for the protected binding.

### Backpressure and roles

**SNTR-WS-100**, **SNTR-WSS-100** — All core/channel/principal bounds MUST
apply, including support for at least 16 concurrent calls and documented
maximum, independent execution accounting, pending input/output counts and
bytes, and absolute deadlines. TLS/WS flow control is no buffering exemption.

**SNTR-WS-101** — Excess lawful call admission MUST return one
`RESOURCE_EXHAUSTED` result without sacrificing already-admitted work. Full
notification capacity drops newest with loss accounting only for notifications
without the recovery contract, while allowing terminal/control progress. For
host-side recovery-notification overflow, the host MUST terminate only the
affected subscription with the targeted termination signal specified in
[recovery §7](recovery.md#7-bounds-overflow-and-authorization); if that signal
cannot be queued, it MUST explicitly close the exhausted connection.
Initiator-local recovery overflow follows that section's explicit
termination/recovery-needed policy. Outbound saturation MUST terminate the
connection as `RESOURCE_EXHAUSTED`; never silently discard selected results or
grow beyond bounds. Record/frame oversize is fatal; event overload follows its
bounded stream policy.

**SNTR-WS-102** — Initiators MUST expose loss separately from application
errors and use bounded jittered backoff for permitted retries, never tight loops
or automatic mutation replay.

**SNTR-WS-110** — WS MUST NOT claim WSS TLS properties. Carrier 3 additionally
requires all [security](security.md#3-carrier-trust-and-tls) checks; enabling a
wrapper or accepting forwarded metadata does not establish those properties.

**SNTR-WS-120**, **SNTR-WSS-120** — New WS/WSS connections MUST perform fresh
Noise and core authentication, with fresh correlation namespace and explicit
recovery/subscriptions. No traffic state, unfinished RPC or session migrates,
even with the same valid AK. Connection IDs are not resume credentials.

**SNTR-WS-200**, **SNTR-WSS-200** — Clients MUST validate every carrier layer,
the exact path/token and 101 before M1, validate M2 before encrypted hello,
then await ready. WSS verifies TLS chain/name first. Per-attempt/per-call timers
and receive bounds are mandatory.

**SNTR-WS-201** — Clients MUST use RFC 6455 masking, binary messages, bounded
fragment reassembly and Ping replies. Clean Close is attempted within the
budget unless failure requires abort; no indefinite teardown wait is allowed.

**SNTR-WS-202**, **SNTR-WSS-201** — Clients MUST keep credentials out of Upgrade,
fail closed on trust/selection failure, re-validate each new endpoint, treat
Origin as non-authority and explicitly reauthenticate/recover after reconnect.
No carrier/format fallback or identical rejected-trust retry is automatic.

**SNTR-WS-210**, **SNTR-WSS-210** — Hosts MUST validate Upgrade before 101,
enforce rate/concurrency bounds and emit only one core handshake outcome after
fresh confirmation and current host authentication. WSS presents a valid
intended certificate and enforces verified TLS ≥1.3.

**SNTR-WS-211** — Hosts MUST validate shape before policy, bind one principal,
authorize before dispatch and forbid pre-ready notifications/effects. They
enforce every bound with principal isolation; Ping replies MUST NOT wait for
application handlers.

**SNTR-WS-212** — Hosts MUST document endpoint, Origin, disabled compression,
count/byte/time limits, admission and close/drain policy. These limits MUST be
enforced.

**SNTR-WSS-211**, **SNTR-SCW-007** — The WSS host MUST terminate TLS itself.
Forwarding headers or caller-terminated TLS cannot assert carrier 3.

**SNTR-WS-220**, **SNTR-WSS-220** — Failures MUST be bounded/deterministic,
without panic, unbounded allocation, sensitive disclosure or synthesized remote
results. Downgrade/proxy inconsistency closes rather than falls back. Ordinary
RPC overload remains per-call unless connection or outbound capacity is
exhausted.

**SNTR-WSS-110**, **SNTR-WSS-111**, **SNTR-WSS-112**, **SNTR-WSS-113** — WSS
MUST apply `SNTR-TSEC-002`–`004/007`: established verified TLS ≥1.3, chain,
hostname/SNI, expiry/revocation policy and no downgrade.

**SNTR-WSS-114** — WSS MUST apply direct-host termination and reject proxy
carrier assertions under `SNTR-TSEC-008/031`.

**SNTR-WSS-115** — WSS certificate rotation MUST follow `SNTR-TSEC-006`,
independently of mandatory Noise pin rotation under `SNTR-DAUTH-024`.

## 6. Limits and deadlines

**SNTR-SCW-012** — Every carrier MUST enforce finite documented budgets,
including the ceilings below. Total establishment MUST complete
within 15 seconds, and Noise establishment plus first encrypted hello and
fresh client confirmation share a 5-second absolute limit. Deployments MAY
shorten these positive limits, never extend them. A 24-hour channel lifetime
is not an establishment allowance. Caller deadlines may shorten any operation;
moving between phases MUST NOT start a fresh attempt budget.

| Operation | Maximum |
|---|---:|
| Total resolution/socket dial + TLS if applicable + Upgrade if applicable + Noise + core readiness | 15 s |
| Channel establishment and first encrypted hello/confirmation | 5 s |
| Next complete record, including idle/partial input wait | 24 h |
| Frame assembly from first incomplete authenticated plaintext | 24 h |
| One entire frame's encrypted output, not one fragment/record at a time | 10 s |
| Carrier teardown after close | 24 h |
| Channel age including establishment, idle and suspend | 24 h |
| Protected records per direction | `2^32` |
| Pending operations per direction, including active work | 1,024 |
| Buffered outbound frames | 1,024 |

Channel establishment and first hello share a single absolute channel limit;
neither M2 nor first partial/complete record resets it. The independent core
timer in [connection](connection.md) cannot extend channel or total readiness
limits. Frame assembly begins with incomplete authenticated plaintext and is
not postponed by backpressured delivery or refreshed by trickle records.
Ping/Pong, partial reads and internal state transitions do not extend deadlines.

Hosts MUST separately bound accepted connections, unauthenticated handshakes,
store and cryptographic work, pending calls, surviving executions, selected
output, pending input/output counts and bytes, reassembly and subscription/replay
state, both per principal and in aggregate. Excess admission is refused
immediately. Count and byte bounds are both required; local limits MAY be lower
than the ceilings above. Work that survives cancellation or connection loss remains
accounted until it stops.

The [RPC emission rules](rpc.md#3-one-elapsed-deadline-and-one-terminal-outcome)
MUST be applied once immediately before carrier handoff/encryption. An expired
or otherwise terminal request is not sent. Live requests carry positive
remaining milliseconds rounded down; less than one millisecond expires locally,
never as `timeout_ms=0`. Once a nonce is consumed, exact ciphertext MUST finish
in order or the connection aborts. Cancellation cannot splice, re-encrypt or
reconsider fragments of that output. Pending output MUST NOT indefinitely block
cancellation, deadlines or terminal/control progress.

At 24 hours or record-count exhaustion, the channel MUST close without further
protection/delivery or counter wrap. Renewal requires fresh keys, a fresh
handshake and explicit recovery. Suspend-inclusive age MUST be checked before
buffered delivery after wake. Traffic cipher state MUST NOT be persisted,
migrated or resumed across host/process restart.

Each connection attempt has independent channel and authorization state.
Data from an unsuccessful attempt MUST NOT be processed on a replacement.
Readiness does not reset an already-started record or frame deadline.
Shutdown MUST preserve selected outcomes and reserve time for carrier teardown
within its total absolute deadline. A graceful drain does not establish that
pending ciphertext was delivered or that application effects stopped.

## 7. Failure handling

Malformed outer framing, context/authentication failure, nonce/lifetime failure
and incomplete units terminate without partial dispatch or resynchronization.
Complete-boundary EOF is loss, not authenticated completion. Local causes and
native peer observations remain separate under [connection](connection.md#2-failure-reporting).
Ordinary post-ready `PERMISSION_DENIED` leaves the connection usable; binding
withdrawal `UNAUTHENTICATED` settles other calls and closes. A bounded denial
drain is not authenticated delivery, a new grace period or permission to emit
protected work after withdrawal.

### TLS layering

TLS requirements apply to WSS. Encrypted raw TCP requires Noise and host
authorization, not outer TLS; WS is restricted loopback development without
outer TLS. Neither clear frame carriage nor standalone TLS/TCP is a binding.

**SNTR-TLS-001**, **SNTR-TLS-009** — TLS records MUST NOT be interpreted as
Syntra envelope/record boundaries or as permission for clear frame carriage.
The selected carrier still uses this document's mandatory Noise record stream.

**SNTR-TLS-002**, **SNTR-TLS-003**, **SNTR-TLS-004**, **SNTR-TLS-005** — Where
outer TLS is specified (WSS), TLS version, chain/name verification and failure
gating MUST follow `SNTR-TSEC-002`–`004/007/009`, before M1 or credentials.

**SNTR-TLS-006**, **SNTR-TLS-030** — WSS hosts MUST present valid intended TLS
identity and apply direct-host termination. Proxy assertions cannot establish
the required carrier identity.

**SNTR-TLS-007** — No Syntra raw-TCP ALPN token is defined. WSS MUST use its
HTTP/1.1 ALPN rules rather than inventing a Syntra ALPN fallback.

**SNTR-TLS-008** — Additional deployment client certificates MUST NOT substitute
for hello/current host identity policy, merge privileges or imply a standardized
TLS-exporter credential binding. No mTLS-specific Syntra principal mechanism
is defined.

**SNTR-TLS-010**, **SNTR-TLS-011** — TLS shutdown/session tickets MUST NOT
imply application success, logical-session recovery or restored traffic state.
Backpressure, elapsed deadlines, liveness and bounded close remain those of
the selected carrier and [connection](connection.md).

**SNTR-TLS-020** — Initiators MUST fail closed and revalidate configured TLS
identity before secrets wherever that outer layer is required.

## 8. Terminal-only output

Only the [scoped terminal transition](connection.md#6-scoped-terminal-receipt)
may permit its reserved result after its exact owned withdrawal. This is the
narrow exception to §7's protected-output prohibition, not a denial drain or
permission to complete unrelated output after withdrawal. Carrier selection,
context bytes, framing, encryption and trust checks remain unchanged. Raw frame
drivers, record adapters and custom byte pumps need the entire fence,
observation and handoff contract or reject reservation before mutation. Support
for this operation cannot activate an otherwise unsupported carrier.

**SNTR-TRC-006** — Before allowing the application transition to start, host and
driver reservation MUST stop new protected admission and ordinary egress on
that connection, suppress unstarted ordinary output, reserve bounded writer/
result capacity and establish a complete outbound-frame boundary. Sibling calls
and subscriptions MUST lose delivery eligibility; cancellation does not imply
their effects stopped. Failure to establish the boundary within budget MUST
close without starting the terminal mutation.

The fence covers runtime queues, notifications, recovery, selected replies and
driver-buffered output. Independent embedder ingress checks and authority
supervisors participate in the same coordination; driver support alone cannot
prevent an independent socket close. Inbound protected requests are never
dispatched after the fence. Malformed input, authentication failures and carrier
loss retain terminal precedence. A hard denial during quiescence aborts rather
than finishing ordinary output under the exception.

**SNTR-TRC-007** — A partially emitted ordinary frame MUST finish within the
pre-mutation budget or force abort. It MUST NOT be dropped and followed by a
receipt. Once encryption consumes a nonce, the exact ciphertext MUST finish in
order or the connection MUST abort; drivers MUST NOT splice frames, skip nonces,
re-encrypt replacements or restart an entire partially emitted unit. These rules
also apply to a partial receipt. Quiescence is pre-mutation, never permission to
finish unrelated protected output after withdrawal to reach a receipt in a FIFO.

**SNTR-TRC-009** — Host and driver MUST set the final deadline to the earlier of
the initiating request deadline and **five seconds** after reservation begins.
The final quarter of that initial remaining budget, capped at **250 ms**, MUST
be reserved for teardown. Quiescence, authority I/O, application completion,
selection and result writing MUST finish before that teardown tail. Insufficient
clock resolution or remaining budget MUST reject reservation before mutation.
Deadlines MUST NOT be extended by retries, progress, repeated callers or adapter
completion. Earlier security, channel-age and record limits remain binding.

These budgets apply across all records and carrier fragmentation of the receipt;
applications may impose stricter limits. Conservative elapsed/deadline semantics
include suspension. Detected clock discontinuity closes instead of buying more
time. Application work surviving its budget remains accounted without postponing
carrier closure.

**SNTR-TRC-011** — Driver and authority adapter MUST consume receipt eligibility
once, at the final validated handoff to the sole carrier writer, bound to the
exact result and original connection. The handoff MUST use a fresh,
operation-aware authority observation; cached generic validity alone is
insufficient. Checks and blocked-I/O repolls MUST keep external denial, unknown
authority, deadline and hard transport failures fail-closed. A local lock MUST
NOT be held across an application transaction or unbounded authority I/O.

The adapter declares freshness/read/close bounds within existing security limits.
Observation and carrier I/O are not a distributed atomic transaction. A later
superseding event can race bytes already handed to the carrier; those bytes
cannot be recalled. There is no instantaneous distributed cutoff, rollback of
emitted bytes or permission for a longer cached allow. An application needing
atomic remote permission consumption needs a stronger coordinated authority
contract. After completion or failure the carrier closes and channel state is
retired, with [retained cleanup ownership](connection.md#6-scoped-terminal-receipt).
