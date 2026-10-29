# Secure channel and device authorization acceptance plan

- Status: accepted companion plan for RFC 0007; formal cases are registered in [`../manifest/sc1-wss.yaml`](../manifest/sc1-wss.yaml), but registration is not execution.
- Owner: `rfcs/0007-secure-channel-device-authorization.md`.
- Requirement owners: `specifications/security/secure-channel.md`
  (`SNTR-SC-001` through `SNTR-SC-015`),
  `specifications/security/device-authorization.md`
  (`SNTR-DAUTH-001` through `SNTR-DAUTH-010`) and
  `specifications/transports/noise-bindings.md`
  (`SNTR-SCW-001` through `SNTR-SCW-012`).
- Profile: `SNTR-SC1-WSS-V1`; see [`../profiles.yaml`](../profiles.yaml).
- Evidence: the Rust implementation records local and same-implementation
  integration checks in its `AUDIT.md` and `docs/implementation-status.md`.
  Independent Rust–Go interoperability, executed `CONF-SCW-*` verdicts and
  independent security review remain outstanding.

## 1. Scope, authority, and prerequisites

This document retains the manual-observation plan and its historical
draft-1 evidence. The normative v1 contract is RFC 0007 §11.4 and
`specifications/transports/noise-bindings.md`; the executable case
specifications are `../manifest/sc1-wss.yaml`. All 33 `PLAN-*` references below
are local planning references, not registered `CONF-*` tests or executed
results. The `CONF-SCW-*` cases are registered; no verdict is implied.

RFC 0007 is accepted, but acceptance does not authorize a stable release or
establish secure-channel, device-authorization or UDP conformance. The existing
profiles and claim rules continue to define their own boundaries. TCP/WS remain
restricted development carriers, WSS is the public profile, and UDP is deferred.

### Implementation evidence versus acceptance

The following observations were executed for the historical experimental
draft-1 implementation. The
ledger records environment, scope and limitations. This mapping is not a
per-`CONF-*` result declaration and does not turn `PLAN-*` into test IDs.

| Plan references | Executed implementation evidence | Still required for complete acceptance |
|---|---|---|
| `PLAN-SC-001`–`PLAN-SC-005` | Both suites, canonical context, empty payloads, key/context rejection, fresh ephemerals and injected entropy failure | Independent vectors and dependency/composition review |
| `PLAN-SC-006`, `PLAN-DAUTH-005`, `PLAN-DAUTH-010` | Fresh-client-record gate, explicit channel policy, deny-by-default methods, hello/ready and no implicit empty-credential authorization | Host root-identity/current-enrollment policy validation; the bridge does not enforce principal equality |
| `PLAN-SC-007`–`PLAN-SC-010`, `PLAN-TCP-001`, `PLAN-WS-001` | Record/frame bounds, split/coalesced reconstruction, invalid records, ordered failure and key-use/lifetime tests | Independent record/cross-carrier exchange and remaining security cases |
| `PLAN-SC-011`, `PLAN-SC-012`, `PLAN-TCP-002`, `PLAN-TCP-003` | Absolute clocks, admission/caps, stalled writer progress, nonce-safe cancellation, bounded drain and shutdown regressions | Aggregate deployment budgets and assumptions for cancellation-compliant I/O/store callbacks |
| `PLAN-SC-013`, `PLAN-SC-014`, `PLAN-DAUTH-009` | Explicit mode/carrier, no fallback, fresh sessions after restart and faults | Accepted renewal/recovery semantics; no automatic replay or complete recovery service |
| `PLAN-SC-015` | Measured benchmarks and scoped verification results documented without superiority/audit/conformance claims | Independent review and normal acceptance/claim process |
| `PLAN-DAUTH-001`, `PLAN-DAUTH-003`, `PLAN-DAUTH-004`, `PLAN-DAUTH-008` | Nonzero key/context validation, preprovisioned lookup, generic denial and no raw-key formatting | Issuance entropy/collision discipline, protected storage, store timing/privacy and deployment rate limits |
| `PLAN-DAUTH-006` | Local expiry, idle revocation and principal-disconnect regressions | Deployment propagation guarantee; no container revocation case |
| `PLAN-DAUTH-002`, `PLAN-DAUTH-007` | Only preprovisioned bootstrap/returning fixtures | Enrollment transaction, protected delivery/ack recovery and complete rotation workflow |
| `PLAN-UDP-*`, `PLAN-INTEROP-001` | Not executed | Complete UDP design and independent both-role interoperability respectively |

Before converting a planned case to a formal executable manifest, record the
accepted RFC revision. The implementation resolves several former design TBDs:

1. Exact suite names, authenticated context serialization (field order, lengths,
   encodings, domains, and versioning), trusted server-key provisioning, and
   handshake/carrier selection. Context equality means exact bytes, not equality
   after parsing or normalization. The exact experimental bytes now exist in the
   [carrier contract](../../specifications/transports/noise-bindings.md); their
   acceptance and independent validation remain open.
2. Carrier record headers, lengths, segmentation/reassembly rules, error/close
   mapping, and which bounds count headers, ciphertext, tags, and plaintext.
   TCP/WS/WSS draft-1 mappings are implemented and documented; UDP remains deferred.
   Existing baseline profiles are not redefined by experimental execution.
3. Fresh client traffic confirmation, the channel-context host authentication API,
   enrollment extension/RPC approval, credential lifecycle policy, and ordering
   relative to Syntra readiness and protected method dispatch. The channel hook
   and fresh-record sequencing are implemented; enrollment lifecycle remains
   incomplete. No new
   `ServerReady` field or enrollment RPC is allocated by this plan.
4. Concrete timeout, queue, lookup, aggregate-memory, key-lifetime, revocation,
   and rotation-overlap limits, with deterministic clocks/fault injection and
   observable accounting. Concrete adapter/server/writer limits are recorded in
   the ledger. Rotation overlap and deployment-wide guarantees remain open.
5. UDP counter encoding/window rules, authenticated path validation and
   anti-amplification accounting, and any reliability, retransmission, or
   fragmentation contract. Those features are unsupported before an accepted RFC.

## 2. Planned fixture and observation method

Each applicable case is planned for both initiator and host roles. Set up a
trusted fixture server key, isolated per-device credentials, a neutral protected
echo method, a denied method, a policy-controlled enrollment operation, and
instrumented peers. Record the suite/library versions, carrier mapping revision,
bounds, role, injected fault, externally visible result, dispatch counts, state
transitions, and bounded resource counters. Inspect secret hygiene with synthetic
markers in isolated fixtures; retain only redacted diagnostics as evidence.

For success paths, observe authenticated plaintext reaching the correct Syntra
state and only the permitted handler. For rejection paths, observe zero protected
effects, the proposed terminal or discard behavior, bounded cleanup, and no
secret-bearing peer diagnostic. Exact carrier close codes and local error enums
await the accepted mapping; do not infer them from another profile's tests.

Use reviewed, established Noise implementations, controllable randomness failures,
allocation/write hooks, and injected clocks. Deterministic crypto fixtures will
need independently checked provenance and complete inputs after context bytes are
fixed. This plan supplies no fabricated golden ciphertext. Statistical samples
alone do not prove entropy quality or the absence of timing oracles.
The empty-payload Noise bodies total **96 bytes** in either mode. Canonical v1
carries the `37 + S`-byte context, where scope byte length `S` is 1–255:
**134–388 bytes before carrier framing**, or **138–392 bytes over TCP**
including the two length prefixes. These exclude carrier establishment, Syntra
hello/ready and traffic confirmation; they are not total readiness costs.

## 3. Secure-channel requirement cases (all manual / planned)

### PLAN-SC-001 — suite and implementation selection

Maps `SNTR-SC-001`.

- Success: perform NK bootstrap and NKpsk0 reconnect with the exact proposed
  suite using an established implementation; verify peer authentication and
  correct directional transport keys through protected traffic. Check the raw
  handshake lengths using the accounting in §2.
- Negatives: wrong server key, wrong PSK, unsupported pattern/suite, malformed
  handshake, and NK/NKpsk0 mode confusion fail without protected dispatch or
  substitution of a custom handshake. Review dependency provenance and suite
  configuration; wire success alone cannot prove library selection.

### PLAN-SC-002 — layer separation

Maps `SNTR-SC-002`.

- Success: review that the channel/library handles cryptography, adapters handle
  carrier bytes, and core receives the same logical Syntra envelopes; repeat
  equivalent logical exchanges across proposed carriers after mapping approval.
- Negatives: malformed encrypted carrier input never reaches protobuf decoding
  or host authorization; changing adapters cannot select a different principal
  or bypass channel verification. Flag core dependencies on socket/library
  internals and duplicated cryptography as review failures.

### PLAN-SC-003 — exact authenticated context

Maps `SNTR-SC-003`.

- Success: once serialization is accepted, independently construct identical
  context bytes on both peers and complete the handshake. Review coverage of
  suite/version, roles, carrier binding, server identity, and lookup handle as
  specified by that contract.
- Negatives: alter one byte of each bound component, swap roles/carriers, omit
  or reorder fields, or use an ambiguously encoded length; authentication fails
   without dispatch. Use the canonical v1 context vectors for exact checks;
   semantic equivalence is not a substitute for transcript binding.

### PLAN-SC-004 — empty handshake payloads and no early effects

Maps `SNTR-SC-004`.

- Success: both handshake payloads are empty; application authentication and
  protected requests occur only in the later approved Syntra flow.
- Negatives: place enrollment data, credentials, an RPC, or other non-empty
  payload in either handshake message; reject with no enrollment, handler call,
  principal grant, or queued early work replayed after readiness.

### PLAN-SC-005 — ephemeral freshness and random-source failure

Maps `SNTR-SC-005`.

- Success: observe a new ephemeral for each role on initial connection,
  reconnect, concurrent attempt, and retry that starts a new handshake attempt;
  review use of a suitable random source rather than inferring its quality from
  non-repetition. Where an accepted datagram binding retransmits within the same
  attempt, preserve its exact cached handshake bytes and state rather than
  regenerating a message or advancing the handshake again.
- Negatives: inject entropy acquisition failure before each generation; abort
  before sending dependent handshake bytes. Detect ephemeral reuse across
  distinct attempts, deterministic production seeds, and fallback to weak
  randomness in review. Same-attempt retransmission is not a freshness failure.

### PLAN-SC-006 — fresh client confirmation and Syntra readiness

Maps `SNTR-SC-006`.

- Success: the host observes fresh authenticated client traffic under the new
  channel keys; approved host authentication binds the principal/scope, and
  Syntra readiness completes before a permitted protected method has an effect.
  On the initiator, observe that an encrypted `hello` is emitted only after
  successful verification of the second Noise handshake message (M2).
- Negatives: replay the first NKpsk0 flight, stop after the host reply, replay
  old transport ciphertext, inject a pre-ready request, or deny host policy.
  None grants protected access. Handshake completion alone is insufficient;
   verify the documented confirmation/API sequencing rather than assuming that
   handshake completion or the asynchronous validity checker performs host policy.
- Initiator negatives: delay or omit M2, then corrupt its tag/body or use an
  inconsistent authenticated context. Before successful M2 verification,
  assert zero emitted `hello` or credential bytes, not merely zero host handler
  dispatches. Missing M2 reaches the absolute establishment deadline without
  releasing queued Syntra data; invalid M2 terminates the attempt.

### PLAN-SC-007 — standard records, empty AD, and length limits

Maps `SNTR-SC-007`.

- Success: exercise standard transport encryption with empty associated data
  (AD), plaintext lengths through 65,519 bytes and ciphertext through 65,535
  bytes including the 16-byte tag. Independently decrypt and compare plaintext.
- Negatives: 65,520-byte plaintext, 65,536-byte ciphertext, truncated tag,
  changed tag/body, and a peer using non-empty AD cannot yield accepted
  plaintext. Review that adapter metadata does not silently customize the
  standard library's AD or nonce processing.

### PLAN-SC-008 — bounded logical frame reconstruction

Maps `SNTR-SC-008`; carrier expansion: `PLAN-TCP-001`, `PLAN-TCP-002`,
`PLAN-WS-001`, `PLAN-UDP-003`.

- Success: reconstruct a valid serialized Syntra `Frame` of exactly 1 MiB
  (1,048,576 bytes) across bounded authenticated records where the accepted
  mapping permits segmentation; dispatch exactly once after complete validation.
- Negatives: a declared logical length of 1,048,577, overflowed length, or
  aggregate segments exceeding the bound is rejected before allocation of the
  declared oversized frame. Partial authenticated segments never trigger decode
  or dispatch; inspect allocation counters, including carrier accumulators.

### PLAN-SC-009 — directional nonce/key ownership and lifetime

Maps `SNTR-SC-009`; cancellation expansion: `PLAN-TCP-003`.

- Success: concurrent sends serialize ownership of each directional cipher
  state; every encrypted record consumes a unique nonce under that key.
  Expiry/usage limits trigger the approved fresh-handshake/reconnect policy.
- Negatives: race two writers, exhaust a counter/lifetime, cancel after
  encryption, fail a write, and reconnect. Never roll back/reuse a consumed
  nonce, wrap counters, swap directional keys, or restore old cipher state.
  Uncertain stream progress closes the connection rather than re-encrypting at
  the same nonce or leaving the peer desynchronized.

### PLAN-SC-010 — fail-closed errors and secret hygiene

Maps `SNTR-SC-010`.

- Success: valid records remain usable until a defined close condition; failure
  diagnostics are generic and contain no AK/PSK, private key, traffic key,
  decrypted secret, or raw untrusted payload.
- Negatives: corrupt every handshake/record component, use a wrong key, and
  inject decrypt/internal errors. No failed authentication yields plaintext,
  protected effects, or error-dependent retry/fallback. Review peer-visible
  content, close behavior, and bounded timing distributions for an oracle;
  uniform text alone does not establish oracle resistance.

### PLAN-SC-011 — timeouts, queues, and aggregate limits

Maps `SNTR-SC-011`.

- Success: at documented limits, use injected clocks and accounting to complete
  handshakes and sustain bounded bidirectional queues, then drain and release
  resources within the declared budget.
- Negatives: silent/slow handshakes, stalled readers, flooded records, many
  simultaneous connections, and partial-frame accumulation reach defined
  deadline/admission behavior. Assert per-connection and aggregate byte/item/
  attempt limits, no unbounded deferred work, and recovery of capacity after
  rejection. Exact budgets and load model are acceptance blockers if absent.

### PLAN-SC-012 — EOF, cancellation, and shutdown

Maps `SNTR-SC-012`; expansion: `PLAN-TCP-002`, `PLAN-TCP-003`.

- Success: finish a complete authenticated frame, perform the approved bounded
  shutdown, release readers/writers, and discard channel state on closure.
- Negatives: EOF at every prefix/body/tag boundary, cancellation during read,
  encryption, or write, and simultaneous peer/local shutdown never expose a
  partial frame, report truncated work as successful, hang tasks, or retain
  reusable keys/nonces. In-flight operation outcomes follow the accepted core
  loss/cancellation rules rather than inferring execution from transport receipt.

### PLAN-SC-013 — no silent fallback

Maps `SNTR-SC-013`.

- Success: explicit proposed secure-channel configuration establishes only its
  selected mode and accepted suite.
- Negatives: strip/change selection, offer plaintext or a different security
  mode after failure, or simulate an unavailable secure endpoint. Fail closed
  without automatically resending credentials or requests through a weaker or
  different mode. Review defaults and retry paths as well as observable bytes.

### PLAN-SC-014 — reconnect is separate from session recovery

Maps `SNTR-SC-014`; related `PLAN-DAUTH-009`.

- Success: reconnect uses a fresh handshake and cipher states, repeats host
  authorization and Syntra readiness, and treats any separately approved
  application-session recovery as a distinct negotiated operation.
- Negatives: old channel records, counters, session identifiers, pending RPCs,
  or cached principal state do not silently reactivate a connection. An AK
  reconnect proves no session resumption or reliable-delivery capability.

### PLAN-SC-015 — evidence and claim boundaries

Maps `SNTR-SC-015`.

- Success: manually review declarations, release text, and retained evidence
  for exact scope, proposal status, implementation versions, and executed-case
  references when those eventually exist.
- Negatives: reject unsupported post-quantum, performance, audit, production,
  or conformance claims; a design review, byte-count estimate, unit test, or
  planned interop run supplies none of those assurances. No new active profile
  or conformance badge is created by this plan.

## 4. Device-authorization requirement cases (all manual / planned)

### PLAN-DAUTH-001 — per-device authorization key

Maps `SNTR-DAUTH-001`.

- Success: enroll two devices with separate 32-byte random authorization keys
  (AKs); use each actual AK as the PSK for its NKpsk0 reconnect. Review entropy
  sourcing and per-device isolation.
- Negatives: wrong length, entropy failure, device-key reuse, signing-key
  substitution, or presenting the AK as a bearer credential does not authorize
  reconnect. A handle or captured reconnect transcript without the AK is
  insufficient; review that the design uses symmetric proof of possession.

### PLAN-DAUTH-002 — authenticated bootstrap enrollment

Maps `SNTR-DAUTH-002`.

- Success: verify the trusted server identity during bootstrap, authenticate
  the enrolling principal, and have host enrollment policy explicitly approve
  device enrollment before persisting an authorized record.
- Negatives: server-key mismatch, unauthenticated/anonymous bootstrap, denied
  policy, premature enrollment, or replayed enrollment attempt grants no device
  authority. NK server authentication alone does not authenticate the client
  principal or authorize enrollment.

### PLAN-DAUTH-003 — bounded public lookup handle

Maps `SNTR-DAUTH-003`; context expansion: `PLAN-SC-003`.

- Success: use exactly an 8-byte public handle for bounded record selection,
  bind it into the accepted authenticated context, and review collision
  handling plus documented linkability/privacy and lookup limits.
- Negatives: possession alone, a handle/PSK mismatch, altered handle, wrong
  length, forced collision, or cross-principal collision grants no authority.
  Collisions fail or are resolved by the approved bounded procedure; never
  overwrite another principal's record or try an unbounded list of keys.

### PLAN-DAUTH-004 — actual PSK storage and hygiene

Maps `SNTR-DAUTH-004`.

- Success: reconnect after restart by retrieving the actual PSK from approved
  protected storage, wrapped at rest with access controls and lifecycle cleanup.
- Negatives: hash-only storage cannot substitute for the required PSK; missing
  wrapping key, corrupt wrapped material, unauthorized read, or unwrap failure
  fails closed. Inspect logs, traces, errors, and persistent diagnostics for
  synthetic AK markers; neither AK nor unwrapped PSK is logged or echoed.

### PLAN-DAUTH-005 — principal, scope, and method authorization

Maps `SNTR-DAUTH-005`.

- Success: persist enrollment binding to one principal and explicit scopes;
  reconnect restores only that binding and permits the allowed fixture method
  after fresh confirmation and readiness.
- Negatives: change principal/scope inputs, substitute another device record,
  invoke a denied method, or reuse stale authorization. No privilege union,
  scope escalation, or protected side effect occurs; method checks remain
  required after successful channel authentication.

### PLAN-DAUTH-006 — expiry and revocation including active channels

Maps `SNTR-DAUTH-006`.

- Success: valid keys work before expiry; injected-clock expiry and explicit
  revocation take effect within the documented propagation bound on both new
  reconnects and already active channels.
- Negatives: race a protected call/reconnect with revocation, advance past
  expiry, or serve a stale cached record. Access stops per the approved active-
  channel invalidation policy; no indefinite authorization from a once-valid
  handshake. Record enforcement ordering and in-flight effect policy as blockers
  if the proposal leaves them unspecified.

### PLAN-DAUTH-007 — rotation, overlap, concurrency, and crash recovery

Maps `SNTR-DAUTH-007`.

- Success: rotate old to new AK under approved policy, allow only the documented
  bounded overlap, retire the old record, and reconnect with the new key after
  restart. Track active channels under the lifecycle policy.
- Negatives: race rotation/enrollment/reconnect/revocation; crash before and
  after each durable update; retry duplicate operations. No indefinite overlap,
  resurrection of a retired key, inconsistent principal/scope, or partially
  committed authorization survives. Transaction boundaries and overlap windows
  need an approved contract before an exact executable oracle is possible.

### PLAN-DAUTH-008 — bounded lookup and generic refusal

Maps `SNTR-DAUTH-008`.

- Success: a known active record resolves within documented lookup/rate/attempt
  budgets and reconnect succeeds with the matching PSK.
- Negatives: compare unknown, expired, revoked, malformed, collision, and wrong-
  PSK attempts under flood and concurrent load. Observe generic peer-visible
  failures without revealing record existence/status, bounded storage queries,
  no key enumeration, and no secret-bearing diagnostics. Review timing/traffic
  distinctions and side effects; do not claim constant-time behavior from a
  small timing sample or identical error text.

### PLAN-DAUTH-009 — cross-carrier fresh authorization

Maps `SNTR-DAUTH-009`; related `PLAN-SC-014`.

- Success: where host policy and accepted mappings permit the same device on a
  second carrier, perform a fresh handshake with carrier-bound context, new
  traffic keys/counters, fresh client confirmation, and Syntra authorization.
- Negatives: copy traffic keys/nonces, replay the first carrier's ciphertext,
  import its channel/session state, or bypass carrier-specific host policy.
  None migrates an authorized channel; separately negotiated session recovery
  cannot replace cryptographic reauthentication.

### PLAN-DAUTH-010 — extension and host API approval boundaries

Maps `SNTR-DAUTH-010`.

- Success: manually review the approved channel-context-to-host-auth API and
  any enrollment RPC/extension contract, including principal/scope binding and
  readiness ordering; only then prepare fixtures using that accepted surface.
- Negatives: invented `ServerReady` fields, undocumented enrollment RPCs,
  ad-hoc credential encodings, or trusting a transport-authenticated flag as
  application authorization block acceptance. Missing APIs or wire decisions
  are explicit blockers, not permission to allocate fields in a test plan.

## 5. Carrier-focused expansion (all manual / planned)

These cases expand the requirement cases above using the informative mappings;
they add no requirement IDs and establish no transport profile.

### PLAN-TCP-001 — arbitrary splitting, coalescing, and segmentation

Maps `SNTR-SC-007`, `SNTR-SC-008`, `SNTR-SC-011`.

- Success: using the canonical v1 header formats, split every record prefix byte,
  encrypted body, and tag across reads (including one-byte reads); coalesce
  multiple records into a read and several logical frames into a stream. Use
  accepted segmentation for a frame larger than one Noise plaintext record,
  through exactly 1,048,576 logical bytes; recover each frame exactly once.
- Negatives: malformed/overflowing lengths, record max+1, declared logical
  max+1, and accumulating segments beyond the logical/aggregate limit fail
  before oversized allocation. Read/write chunk boundaries never become frame
  boundaries; incomplete authentication never exposes partial plaintext to core.

### PLAN-TCP-002 — truncation and reconstruction teardown

Maps `SNTR-SC-008`, `SNTR-SC-012`.

- Success: complete all records for a segmented frame, dispatch once, then
  close at a complete-unit boundary with the approved teardown result.
- Negatives: EOF at each partial prefix, body, and tag position, or between
  authenticated segments of an unfinished frame discards that frame and closes.
  No resynchronization scan, partial protobuf decode, stale accumulator reuse,
  or success for incomplete work; buffered memory is released within bounds.

### PLAN-TCP-003 — cancellation after nonce consumption

Maps `SNTR-SC-009`, `SNTR-SC-011`, `SNTR-SC-012`.

- Success: serialize writers, finish a committed encrypted record with bounded
  queue accounting, and continue only when both peers' nonce progression is
  unambiguous under the accepted cancellation contract.
- Negatives: cancel just after encryption consumes a nonce, before write,
  after partial prefix/body/tag write, and during shutdown; race a second
  sender. Never reuse/roll back that nonce, silently drop a consumed record and
  continue at an unexpected stream counter, or re-encrypt a retry with old
  state. Close on uncertain progress and reconnect with fresh keys; drain vs
  close details remain blocked until the mapping defines atomic write ownership.
- Segmented-envelope continuation: cancel between fully written records of one
  unfinished inner envelope, then enqueue another frame from a second sender.
  Either finish all remaining bytes of the original envelope before subsequent
  output or abort the channel. Assert intact envelope reconstruction at the
  receiver; advancing nonces correctly is not sufficient if the original
  envelope's remaining bytes are silently removed or another frame is spliced
  into it.

### PLAN-WS-001 — encrypted binary mapping and bounds

Maps `SNTR-SC-002`, `SNTR-SC-007`, `SNTR-SC-008`, `SNTR-SC-011`, `SNTR-SC-012`.

- Success: use the proposed encrypted binary-message/record mapping only after
  approval; test binary fragmentation and interleaved control frames, enforce
  ciphertext/message accumulation bounds and the separate reconstructed logical
  frame limit, and deliver authenticated complete frames only.
- Negatives: text, malformed/empty encrypted input, truncated tag, message or
  logical max+1, and Close during assembly cause the accepted rejection/cleanup;
  no unbounded message assembly before decryption. Noise record limits include
  tags; a 1 MiB frame is not one permissible Noise record.
- Compatibility blocker: current WS/WSS profiles map one complete binary
  message directly to one serialized plaintext `Frame`, without an embedded TCP
  prefix. An encrypted record mapping changes that byte contract and needs an
  explicit accepted selection/mapping. Existing WS/WSS expectations supply no
  verdict for these proposed bytes.

### PLAN-UDP-001 — counters, replay, and invalid tags

Maps `SNTR-SC-003`, `SNTR-SC-007`, `SNTR-SC-009`, `SNTR-SC-010`, `SNTR-SC-011`.

- Success, conditional on accepted counter/window rules: authenticate bounded
  datagrams with explicit counters; accept valid out-of-order arrivals within
  the window exactly once and advance authenticated replay state as specified.
- Negatives: duplicates, too-old counters, wrong direction/key/context,
  truncated/invalid tags, and forged far-future counters never dispatch. Invalid
  tags do not shift the replay window or evict valid pending counters; test a
  valid in-window packet after each forgery. Bound counter-state memory and
  work. Counter width, nonce mapping, and replay algorithm remain RFC blockers.

### PLAN-UDP-002 — path validation and anti-amplification

Maps `SNTR-SC-003`, `SNTR-SC-010`, `SNTR-SC-011`, `SNTR-SC-014`, `SNTR-DAUTH-009`.

- Success, conditional on an accepted path contract: validate a return path
  before relaxing its documented amplification/admission bounds; authenticate
  channel traffic and repeat required authorization on a fresh channel.
- Negatives: spoofed source, replay from a changed address, unvalidated path
  change, validation flood, or replayed handshake cannot redirect protected
  traffic or cause output beyond the per-path and aggregate amplification
  budget. Possession of a packet or lookup handle alone validates no new path.
  Exact challenge bytes, accounting ratios, and path-change rules remain blockers.

### PLAN-UDP-003 — loss, reliability, retransmission, and fragmentation

Maps `SNTR-SC-008`, `SNTR-SC-009`, `SNTR-SC-011`, `SNTR-SC-012`, `SNTR-SC-014`.

- Success at the current planning boundary: review declarations to confirm
  reliability, retransmission, and fragmentation remain unsupported before an
  accepted RFC. Later execution needs a complete accepted datagram/MTU and
  bounded reconstruction contract, with separate reliability evidence.
- Negatives planned for that contract: loss, duplication, reordering, oversized
  datagrams, missing/overlapping fragments, reconstruction max+1, retries,
  cancellation, and fragment timeout cannot cause duplicate protected effects,
  nonce reuse, unbounded reassembly, or implicit delivery/session recovery.
  Do not choose retry encryption, ACK, fragment, or retransmission formats here.

## 6. Independent interoperability and eventual evidence

### PLAN-INTEROP-001 — independent Rust–Go exchange

Maps `SNTR-SC-001` through `SNTR-SC-014` and `SNTR-DAUTH-001` through
`SNTR-DAUTH-010`; claim review remains `PLAN-SC-015`.

- Success planned, not executed: pair an independent Rust initiator with a Go
  host, then reverse roles, using independently constructed context bytes and
  reviewed library configuration. Exercise NK bootstrap, policy-approved
  enrollment, NKpsk0 reconnect, fresh traffic confirmation, permitted/denied
  methods, rotation/revocation, and each accepted carrier mapping. Compare
  authenticated context bytes, logical frames, ordering, bounded resource
  observations, and state outcomes, with reproducible redacted logs.
- Negatives planned: suite/context/key mismatch, cross-carrier replay, invalid
  tags, over-limit inputs, early protected requests, revoked keys, and interrupted
  traffic fail on both role pairings without secret disclosure or side effects.
  Self-loopback, shared fixtures alone, and a structural validator pass are not
  independent interoperability evidence.

After RFC acceptance and blocker resolution, register reviewed executable cases
and any separately approved profiles through the normal conformance process.
Only actual executions can populate verdicts and evidence references. Until then,
all 25 requirement rows retain empty `test_ids` and manual acceptance dispositions,
with scoped implementation evidence recorded in their notes and the ledger.
