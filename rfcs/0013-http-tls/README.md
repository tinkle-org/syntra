# HTTP/TLS accepted design bundle

This bundle is **accepted-unadopted**, not the active Syntra contract. The sole
maintainer oscarlaw recorded public acceptance and completed human protocol/security
self-review, with self-approval disclosed, for reviewed source
`cfab7655c348f1d04f4e1d57e28cc1a634478854` in the
[public approval comment](https://github.com/tinkle-org/syntra/pull/25#issuecomment-6688499482).
The [acceptance record](../../docs/decisions/0004-rfc-0011-0014-acceptance.md)
records the decision for [RFC 0013](../0013-http-tls-carriers.md). It succeeds the
pending disposition in the [historical consent record](../../docs/decisions/0003-http-tls-consent.md);
the [dated advisory review](review.md) remains advisory, not independent review.
Design acceptance does not authorize canonical adoption or publisher activation.
Carrier 4/5 allocations and proposed case IDs here are not registered or claimable
in the current conformance suite.

| Artifact | Purpose |
|---|---|
| [contract.json](contract.json) | Exact proposed carrier constants, HTTP operation/ACK mapping, TLS-provider boundary and limits |
| [profiles.yaml](profiles.yaml) | Proposed CARRIER entries, with claimability disabled |
| [cases.yaml](cases.yaml) | Fourteen role-specific test groups, local R13 requirement trace and explicit NOT_EXECUTED verdicts |
| [requirements.yaml](requirements.yaml) | Reciprocal local requirement/case trace, proposed future IDs and owner mapping, not current registration |
| [context-vectors.json](context-vectors.json) | Derived public context bytes for 4/5, with original base IDs and negative recipes |
| [http-vectors.json](http-vectors.json) | Structural HTTP byte fixtures, ACK semantics and CONNECT tunnel-boundary fixtures, not valid Noise ciphertext |
| [owner-delta.md](owner-delta.md) | Activation edits and promotion map for current owners, requirements, registry and candidate tooling |

The validator uses the existing context encoder with an explicit **tool-only**
carrier allowlist; the current fixture generator still admits only 1/2/3. Existing
context bytes, vector IDs/recipes and authoritative Git blobs are not rewritten.
These derived fixtures demonstrate public encoding agreement only. HTTP fixture
lint is not an HTTP peer, TLS/provider implementation or cryptographic test.
The 25 HTTP shapes cover all four operations in both directions plus framing
faults, MAX/MAX+1 bodies, connection retirement and CONNECT. `append_zero_bytes` is a bounded fixture
recipe for synthetic opaque bytes, not valid Noise data or on-wire compression.

Focused check commands from the repository root (not runtime conformance runs):

```sh
python3 -B scripts/check-http-candidate.py
python3 -B scripts/check-http-candidate.py --record-worktree
python3 -B -m unittest discover -s tests -p 'test_http_candidate.py' -v
# Expected exit 2 after successful static validation: canonical adoption pending.
python3 -B scripts/check-http-candidate.py --require-adoption
```

Candidate validation verifies immutable base Git blobs and needs the pinned
base commit. Use a full-history checkout: `git fetch --unshallow` for a
shallow clone, or clone without a depth limit. The local acceptance record must
exist with the exact comment URL and reviewed revision, and the main RFC must
have Status Accepted. During parallel document updates, missing or inconsistent
inputs fail validation; rerun only once those prerequisites are ready. A command
listed here is not evidence that it ran or passed.

The first command validates this isolated proposal. `--record-worktree` emits
JSON with per-file SHA-256, base Git-blob verification, HEAD, dirty state, null
candidate revision, accepted design gates and inactive adoption/release gates.
It includes the actual acceptance record in its source fingerprint and checks
the exact acceptance reference in the contract and local record. This is bounded
local-reference consistency only: static lint does not contact GitHub, verify
GitHub authorization, or independently establish human review. The reviewed
source revision is not the current worktree fingerprint or a release pin.
It checks source hashes and HEAD before
and after validation; its aggregate fingerprint hashes the sorted compact JSON
map of paths to raw file hashes. It writes nothing, commits nothing and
does not promote the bundle. `--require-adoption` deliberately exits 2 because
canonical adoption remains pending, although public approval and human security
self-review are recorded. A green static result does not grant adoption,
execution, freeze or release authority.

Canonical protocol inputs still contain only carriers 1/2/3. Their revision or
fingerprint cannot identify this isolated bundle as activated HTTP support.
Candidate evidence records must identify the exact RFC and bundle fingerprint,
base revision, role, carrier, authentication mode, parameters and observed case
results separately. A snapshot fingerprint identifies reviewed bytes, not
acceptance, execution or conformance. The case definitions include composition
boundaries for immutable policy generations, endpoint-scoped credential release,
absolute deadlines, graceful drain and shutdown outcome accounting; their
runtime verdicts remain NOT_EXECUTED.

R13-T10 separates WSS provider checks (carrier 3) from HTTPS paired-stream checks
(carrier 5). Each entry in `input.variants` is a group with explicit `carriers`,
`scenarios` and group-specific expectations. Select only the group for the tested
carrier and apply both its expectations and the case's shared expectations.
Record separate client/server and bootstrap/returning evidence for each carrier;
WSS has no D stream, so HTTPS pair checks cannot be counted as WSS evidence.
Static group validation neither executes those scenarios nor filters an existing
runtime harness; runtime evidence remains separately required for both carriers.

Public acceptance and human protocol/security self-review are recorded in
Decision 0004, including self-approval disclosure; independent review is not
claimed. Design acceptance leaves canonical adoption deferred. Adoption requires
separately authorized, synchronized canonical specification, registry and fixture changes,
with compatibility and objection dispositions checked against the acceptance record. Only then
may a canonical snapshot identify the adopted contract. A release reference
still requires a real reviewed commit and verified blobs, independent review and
the separate applicable conformance, freeze and publisher authorization gates.
The bundle specifies language-neutral technical behavior, not implementation
packages, callable interfaces or migration instructions. Absolute-form HTTP
forwarding and automatic cross-carrier failover remain outside its permitted
mapping; neither configuration nor local execution evidence changes that scope.
