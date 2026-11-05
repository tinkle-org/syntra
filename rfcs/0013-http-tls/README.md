# HTTP/TLS review candidate

This bundle is **pending adoption**, not the active Syntra contract. It accompanies
[RFC 0013](../0013-http-tls-carriers.md), the
[consent record](../../docs/decisions/0003-http-tls-consent.md) and
[advisory review](review.md). Carrier 4/5 allocations and proposed case IDs here
are not registered or claimable in the current conformance suite.

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

From the upstream repository root:

```sh
python3 scripts/check-http-candidate.py
python3 scripts/check-http-candidate.py --record-worktree
python3 scripts/check-http-candidate.py --require-adoption
python3 scripts/validate-repo.py all
python3 scripts/validate-schema.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Candidate validation verifies immutable base Git blobs and needs the pinned
base commit. Use a full-history checkout: `git fetch --unshallow` for a
shallow clone, or clone without a depth limit.

The first command validates this isolated proposal. `--record-worktree` emits
JSON with per-file SHA-256, base Git-blob verification, HEAD, dirty state, null
candidate revision and pending gates. It checks source hashes and HEAD before
and after validation; its aggregate fingerprint hashes the sorted compact JSON
map of paths to raw file hashes. It writes nothing, commits nothing and
does not promote the proposal. `--require-adoption` deliberately exits 2 while
the public/human gates are missing. A green static result is not acceptance.

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

Canonical snapshot adoption requires public acceptance, the consent record's
human security-review disposition, compatibility decision and any objection
resolutions, and completion of formal acceptance and activation with
synchronized canonical specification, registry and fixture changes. Only then
may a canonical snapshot identify the adopted contract. A release reference
still requires a real reviewed commit and verified blobs.
The bundle specifies language-neutral technical behavior, not implementation
packages, callable interfaces or migration instructions. Absolute-form HTTP
forwarding and automatic cross-carrier failover remain outside its permitted
mapping; neither configuration nor local execution evidence changes that scope.
