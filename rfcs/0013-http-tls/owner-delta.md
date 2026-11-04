# Owner activation delta for RFC 0013

Status: pending adoption. These are staged edit instructions, not changes to
current authority. Public acceptance and applicable human security review are
required before applying them. [Decision 0003](../../docs/decisions/0003-http-tls-consent.md)
does not clear those gates. The [machine contract](contract.json) fixes the
candidate constants; the RFC owns the proposed obligations.

## Transport owner

In `specifications/transports.md` §§1/2, add explicitly configured HTTP carrier 4
and HTTPS carrier 5 alongside 1/2/3, using the candidate registry binding names.
Add 4/5 to the canonical context's carrier value enumeration only; preserve its
encoding, domain, mode, selector, epoch, enrollment handle and scope bytes.
Extend production admission to explicitly authorized HTTP/HTTPS; keep WS
loopback-only and all carriers Noise-protected. Do not wrap clear Frames in HTTP.

Add an HTTP section containing RFC 0013 §§4.1 through 4.5, 4.7 through 4.9,
including the exact POST paths and headers, one record per body, fixed U/D
ownership, counters, input-slot ACK rule, absolute deadlines, native failures,
bounded close, proxies and no-fallback/replay behavior. Cross-reference shared
record, frame, lifetime and first-hello requirements rather than copying offsets.
The HTTP native error table supplements, not replaces, common local error rules.
Preserve the original role-local elapsed origin across all phases and both
streams, the earliest applicable cutoff, independent pause scopes and observable
shutdown failure accounting. Keep absolute-form forwarding and automatic
cross-carrier failover outside this mapping unless separately reviewed and adopted.

## Security and connection owners

In `specifications/security.md` carrier policy and permitted-binding lifecycle,
include explicit HTTP/HTTPS registrations without changing default-deny sets.
An existing enrollment does not acquire additional bindings on reopen. Production
HTTP has Noise protection without outer metadata confidentiality; HTTPS and WSS
also need verified TLS. Preserve the authorization/revocation and pin authority.

Define actual TLS termination by a trusted in-process provider as direct-host
termination. Replace the blanket caller-stream prohibition only to that exact
extent, with RFC §§4.6/4.8/4.10 obligations. Caller booleans, forwarded claims,
remote terminators, tickets and proxy TLS do not attest endpoint TLS. Keep the
independent Noise pin, exact WSS endpoint/token, TLS version/chain/name/current
policy, early-data and ALPN checks for both client and host.
Define policy generations as immutable local snapshots, with independently
stream-bound verification for U/D, no in-place substitution during setup and
fail-closed withdrawal. A retained snapshot never suspends current validity or
revocation checks; matching authorities/deadlines alone do not prove generation
identity. Preserve the explicit-H1 exception for absent ALPN.

In `specifications/connection.md`, include HTTP setup in the existing absolute
attempt budget and native HTTP errors in the peer-observation table. Preserve
strict encrypted hello/current policy/ready and one fixed principal/session.
Cross-reference the distinction between cleanup completion, observed operation
failures and incomplete shutdown; no local shutdown summary may suppress a
failure merely because cleanup finished. Stopping prevents replacement attempts.
In `specifications/rpc.md`, cross-reference carrier-input ACK versus selected
core outcomes and original-unit emission gating. Do not add HTTP-specific RPC
success, replay, deadline or cancellation semantics.

## Requirement and case promotion

The local R13 labels are not registered normative IDs. At acceptance, allocate
the proposed `SNTR-HPC-001` through `SNTR-HPC-029` identifiers if still free,
mapping R13-01 through R13-29 respectively, with no reuse of existing IDs.
Promote the case groups to actual numeric CONF IDs through review, preserving
client/server roles, bootstrap/returning variants, failure assertions and
NOT_EXECUTED evidence. A definition never grants PASS.

| RFC requirements | Destination owner | Candidate cases |
|---|---|---|
| R13-01 through R13-17 | `specifications/transports.md` | R13-T01 through R13-T09; R13-T14 |
| R13-18 through R13-21 | `specifications/security.md` with WSS transport cross-reference | R13-T10 |
| R13-22 through R13-28 | `specifications/transports.md` | R13-T11 through R13-T13 |
| R13-29 | `specifications/security.md` | R13-T14 |

Update `conformance/manifest/requirements.yaml` with reciprocal case references,
actual owner headings and automation scope. Add HTTP/HTTPS entries to
`conformance/profiles.yaml` in its supported schema; `kind: CARRIER` here is a
candidate projection, not permission to silently change the current registry's
`TRANSPORT_PROFILE` schema. Select common cases independently for each new
carrier and add explicit HTTPS-only provider checks. Current WSS needs the
trusted-provider cases too. Do not count a WSS run as HTTPS execution.

## Fixtures and tooling promotion

Preserve all existing context IDs and bytes. Append accepted public 4/5 contexts
and carrier-matched negatives to the canonical JSON/YAML pair; update encoder
allowlists, generator coverage, boundary tests and registry expectations together.
Publish the structural HTTP fixtures under an accepted conformance vector path,
with their explicit non-cryptographic scope. Add request/response admission,
blocked-pump, full-queue and cancellation-race scenarios to actual harnesses.

Synchronize `compatibility/syntra-1.0.json` with the adopted carrier values, exact
paths, registry projection, channel limits and canonical fixture paths. Review
`scripts/validate-repo.py`, context generator, owner synchronization, manifest
schema and selection tests for 4/5 and HTTPS applicability. Keep existing
requirements and compatibility baselines; do not remove tests to hide conflicts.
Update the protocol overview, conformance guide and Unreleased changelog only
when activation is authorized. No source IDL change is required.

## Composition contracts and evidence gates

Channel processing owns Noise verification, key lookup, strict hello and current
host policy. HTTP owns bounded byte admission and U/D scheduling. Complete M1
admission does not await M2 emission; open's 201 still carries exactly one M2.
Each send 204 attests complete input-slot admission only, not decryption,
authentication, execution or effects. Host output records are committed to one
poll response, never cached for retransmission. One selected frame passes its
emission gate once, then remains immutable through ordered completion or abort.
Graceful drain retains the U/D progress needed by that output until the shared
cutoff; stopping admission alone does not prematurely retire one direction.

Stop/completion ownership is registered before concurrent handoff. Cancellation
does not release a running operation's permit or imply completion; incomplete
shutdown retains ownership. Aggregate shutdown observations preserve failures
even after cleanup completes, without exposing private diagnostics or permitting
replacement attempts after stop. Original elapsed origins, remaining allowances
and selected policy generations cover all phases and both streams. Endpoint
selection precedes a credential decision explicitly authorized for that descriptor
and generation. Traffic keys, nonces, callbacks, RPCs and selected outputs do not
migrate on failover or pause/resume. TLS providers perform actual verification
in the endpoint TCB, not remote evidence injection.

Until public/human gates clear, use only the isolated worktree report, not a
canonical HTTP release reference. Evidence identifies the exact reviewed RFC and
bundle fingerprint, base revision, role, carrier, mode, parameters and observed
case results. After synchronization, canonical specification snapshots can
identify adopted inputs; publication still requires an actual reviewed commit
with verified Git blobs. Acceptance, activation, freeze, conformance, independent
security approval and release authorization remain distinct decisions/evidence.
