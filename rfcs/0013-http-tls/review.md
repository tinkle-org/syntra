# RFC 0013 protocol and security advisory review

Date: 2026-11-03. Scope: the uncommitted RFC/candidate on
`feature/http-tls-carriers`, based on
`3f7e8ea037fefcc5c86101d23e7722c83e28a0d3`. Reviewer: AI assistant acting as
drafter/tooling contributor. This is advisory self-analysis, not human security
review, independent review, maintainer acceptance or executed conformance.
The [consent record](../../docs/decisions/0003-http-tls-consent.md) retains the
approval source and missing public evidence. The worktree report hashes the
candidate inputs present when the report runs, without claiming they were
committed. This review does not record that fingerprint.

Revision note, 2026-11-04: the composition contracts and test definitions were
revised as language-neutral technical requirements. The additional dispositions
below remain advisory draft analysis, not human approval or runtime evidence.

## Findings and dispositions

| Finding | Boundary and risk | Correction / evidence still needed |
|---|---|---|
| A01: send ACK waits for higher-layer decryption | A standalone record adapter can wait for an HTTP ACK while a higher driver waits on carrier I/O, coupling the two state machines and stalling hello or fragmented input | R13-09 makes 204 attest atomic complete-record admission into a bounded input slot only. Kernel authentication precedes plaintext use, not HTTP ACK. Runtime blocked-driver/full-queue/fatal-after-ACK tests remain NOT_EXECUTED |
| A02: ambiguous ACK implies authentication | A successful carrier response could be mistaken for client confirmation or RPC delivery | R13-07/09/13 retain host-owned fresh confirmation, strict hello, current policy and loss uncertainty; machine ACK fixture explicitly excludes authentication/effects |
| A03: slot invalidation versus cross-thread callbacks | Cancellation or a wrong-H request can race queued writes/admission and revive a retired slot or invalidate an unrelated slot | R13-08 targets the bound slot; R13-22 requires ownership registration before handoff, stop paths, retained completion observation and generation fencing. Real concurrency testing remains required |
| A04: TLS resumption and policy evidence | An embedder could treat a session ticket or stream boolean as fresh verification, bypassing changed roots, expiry or revocation | R13-18/21 tie actual trusted-provider evidence to each stream and current policy. Resumption cannot bypass checks or send early Syntra data. Real TLS/provider negatives remain required |
| A05: ambiguous Origin input | Multiple Origin values or opaque null origin can accidentally match a permissive middleware rule | R13-04 rejects duplicates and null, uses exact configured serialized-origin matches, permits absent native Origin and grants no identity from it |
| A06: HTTP 204 and CONNECT framing | Applying one Content-Length rule to all statuses or treating CONNECT as a body can desynchronize the stream | Origin 204 forbids CL/TE/body. Successful CONNECT ignores CL/TE and preserves read-ahead per RFC 9110. The offline fixtures distinguish these cases; no network parser correctness is claimed |
| A07: approval conflated with publication/security review | Local consent or AI analysis could incorrectly activate new wire identifiers | Decision 0003 records actual consent and self-approval, leaves public/human gates pending. Candidate registry/contract are isolated and not claimable; validator rejects active-input drift or forged gate flags |
| A08: policy-generation equivalence left implicit | Equal authorities, negotiated parameters or deadlines do not prove that U/D used one trust-policy snapshot; configuration replacement can mix verification policies | R13-02/18 define immutable role-local snapshots and independently stream-bound verification, reject mismatched generations and retire withdrawn selections without freezing validity/revocation. R13-T02/T10 cover the boundary; runtime verdicts remain NOT_EXECUTED |
| A09: budget and credential decisions cross composition boundaries | A fresh per-layer allowance can extend setup, and a credential decision without the selected descriptor can release a secret to an unauthorized endpoint | R13-16 preserves elapsed origin and earliest applicable cutoffs across both streams and required recovery; R13-26 orders descriptor/generation selection before credential release. R13-T09/T13 include handoff, cutoff and endpoint-scoping cases; no execution asserted |
| A10: cleanup completion mistaken for success | An owned operation may exit with failure while resource cleanup completes; suppressing that failure or erasing an earlier incomplete outcome misreports shutdown | R13-22 separates completion and failure with bounded aggregate outcome accounting and no replacement after stop. R13-T11 includes completed-cleanup failure and later-completion cases; runtime verdicts remain NOT_EXECUTED |
| A11: drain or network hints prematurely change lifecycle | Canceling one HTTP direction can destroy pending selected output; an availability hint can accidentally clear an independent application pause | R13-15 retains the U/D progress needed by graceful drain until cutoff; R13-28 requires every applicable pause scope to clear explicitly. R13-T08/T13 specify positive and negative observations; runtime verdicts remain NOT_EXECUTED |
| A12: forwarding and carrier substitution inferred from configuration | Explicit local configuration or a successful connection can be mistaken for permission to use another wire mapping | Section 4.8 explicitly excludes absolute-form forwarding and retains R13-01/26's prohibition on automatic cross-carrier failover. R13-T12/T13 include rejected-route cases; new mappings still need separate review and adoption |
| A13: request eligibility confused with selected result delivery | A call's terminal state or expired deadline could suppress an already-selected host result | R13-12 distinguishes the unsent-request gate from result-output eligibility and preserves success/cancellation/deadline outcomes under independent output/security/shutdown cutoffs. R13-T07 includes each result class; no runtime verdict asserted |
| A14: outage budget mistaken for active-channel lifetime | A late successful establishment might be closed at outage expiry, or core ready might reset probation before required recovery | R13-16/27 define local readiness, release setup/outage I/O gates only then, retain retry accounting until continuous-active reset and stop replacement after unreset exhaustion. R13-T09/T13 cover late readiness and stalled/delayed recovery; no execution asserted |

## Retained threat boundaries

Noise remains mandatory. Canonical context and independent provisioned pins,
fresh randomness, strict hello/ready, empty-credential host policy, same-principal
checks, current authorization/revocation, implicit record ordering and lifetime
bounds remain unchanged. HTTP H is a routing selector, never identity or
resumption authority; its leakage can disrupt availability. Uncertain exchanges
retire both streams without ciphertext retries or automatic RPC replay.

Trusted application TLS code is part of the endpoint TCB and performs actual TLS
in-process. It cannot be modeled as a defense against malicious trusted code;
forwarded claims and external plaintext terminators remain insufficient. Proxy
credentials are independent, protected on the proxy hop and never forwarded to
origins. TLS, poll completion and record admission do not prove exactly-once
effects, durable recovery or stopped external executions.

## Open human review and execution

Human review still needs to resolve carrier/version compatibility against
accepted decisions, public HTTP metadata/DoS acceptance, first-poll routing races,
bounded admission/fairness, real TLS-provider contracts and proxy secret policy.
The proposed counts and timer margins need deployment testing, including large
frames across sequential exchanges within the existing output deadline.
The revised policy-generation, cross-layer deadline, endpoint-scoped credential,
drain, pause-scope and shutdown-reporting obligations also need human review.
They remain proposed additions/clarifications under the existing local R13 IDs,
not amendments to accepted specification owners.

Static fixture validation proves consistency of authored public bytes and
expected assertions only. R13-T01 through R13-T14 need real per-role execution,
negative fault injection and independent evidence; their runtime verdict is
NOT_EXECUTED. No exploitable deployed implementation was examined or approved.

## Succession note — 2026-11-06

The dated advisory analysis above is retained as written, including its then-open
human-review and approval statements. Those pending design-acceptance statements
are succeeded by [Decision 0004](../../docs/decisions/0004-rfc-0011-0014-acceptance.md)
and sole maintainer oscarlaw's
[public approval comment](https://github.com/tinkle-org/syntra/pull/25#issuecomment-6688499482)
for reviewed source `cfab7655c348f1d04f4e1d57e28cc1a634478854`. The maintainer
confirmed completed human protocol/security self-review and disclosed
self-approval. This is not independent review, and this advisory document does
not become a human review merely by linking that decision.

The current bundle status is accepted-unadopted. Acceptance covers the design
only; canonical adoption and publisher activation are deferred. No active owner,
pin, cipher, fixture byte, runtime verdict, freeze or release authority is changed
by that acceptance. Deployment testing and independent execution evidence remain
required. All runtime/formal conformance remains NOT_EXECUTED. The static checker
checks bounded local reference consistency and fingerprints the acceptance
record; it does not verify GitHub authorization or conduct a security review.
