# Conformance manifest format (Section C)

Machine-readable test manifests live in this directory. They are the normative
executable form of the suite; the `*.md` prose companions explain the same
cases for humans. Both share identical test IDs. If they disagree, the cited
`SNTR-*` requirement prevails and the manifest/prose is a bug.

## Design goals

- **Neutral:** YAML 1.2 only (`.yaml` files also parse as JSON-equivalent maps;
  runners MUST NOT need a Protobuf toolchain, Rust, Go, or any test framework
  to read them).
- **Deterministic:** every case states `preconditions`, a concrete `input`,
  and an exact `expected` outcome. No wall-clock flakiness: deadlines use fixed
  budgets with injected-slow handlers or generous margins; expiry uses
  short-lived fixture credentials or injected clocks.
- **Separable:** transport framing (`transport-*.yaml`) is distinct from core
  envelopes (`core.yaml`, `rpc.yaml`); the same logical `Frame` runs over any
  claimed transport with only adapter changes (SNTR-WIRE-901).

## Conceptual example (informative)

```yaml
- id: CONF-RPC-001
  requirement: [SNTR-RPC-001, SNTR-RPC-002, SNTR-RPC-003, SNTR-RPC-006]
  profile: SNTR-RPC-V1
  roles: [client, server]
  capabilities: []
  mandatory: true
  preconditions: [active_session]
  input:
    frames:
      - { request_id: 7, body: request, method: "/example.Echo/Echo",
          payload_b64: "aGVsbG8=", timeout_ms: 500 }
  expected:
    connection_state: ACTIVE
    session_state: unchanged
    frames:
      - { request_id: 7, body: result, payload_b64: "aGVsbG8=" }
```

## Field reference (normative for manifest authors)

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | string `CONF-[A-Z]+-[0-9]+` | yes | Stable test identifier. Never reused; never renumbered. |
| `requirement` | string list `SNTR-*` | yes | Normative requirements under test. Test MUST NOT invent behavior beyond them. |
| `profile` | profile ID or list | yes | One applicable profile, or a non-empty list of independently applicable profiles, from `conformance/profiles.yaml`. |
| `roles` | subset of `client, server` | yes | Which IUT side(s) the verdict applies to. `client-server` in prose = `[client, server]` here. |
| `capabilities` | string list | yes (may be empty) | Capability identifiers required to *execute* (not merely handle absence). Empty = always executed. Placeholder names (`events-v1`, `events-replay-v1`, `resume-v1`) gate Optional cases until their RFCs exist. |
| `mandatory` | boolean | yes | `true` = MUST pass to claim the profile; `false` = Optional (SKIP when capability unclaimed). |
| `preconditions` | string list | yes | Symbolic setup states (see vocabulary below). |
| `input` | map | yes | Stimulus: `frames` (envelope list), `transport` (raw bytes / HTTP / WS actions), `faults` (loss, delay, tamper), `credentials` (throwaway fixture names). |
| `expected` | map | yes | Observable outcome: `connection_state`, `session_state`, `frames`, `error` (`{code, message_pattern}`), `transport` (status/close/alert), `hygiene` (negative-grep list). |
| `control_connection` | map | no | Runner-recognized paired-control scenario for cases whose outcome depends on per-connection negotiation isolation. The runner executes it on a fresh connection with the same host, bound principal, authorization scope, and selector basis as the case-level scenario, then asserts its outcomes in addition to the case-level results. Required `keys`: `preconditions`, `expected`; optional `keys`: `frames`, `subscriptions`, `replay`, `transport`, `faults`, `credentials`, `notes`. Structured fields supersede prose-only controls; a case whose gate attribution relies on a paired control MUST declare it here (e.g., `CONF-URP-001`), and validation rejects prose-only controls for such cases. |
| `notes` | string | no | Human guidance; never adds normative force. |

Precondition vocabulary (closed list; manifests MUST NOT invent new tokens
without an RFC): `no_transport`, `transport_connected`, `handshake_started`,
`active_session`, `anonymous_session`, `expired_credential`,
`revoked_credential`, `valid_chain`, `invalid_chain`, `wrong_hostname`,
`expired_certificate`, `weak_tls_only`, `oversize_ready`, `flood_ready`,
`subscription_confirmed`, `cursor_expired`, `connection_lost`.

Connection-state vocabulary: `CONNECTED`, `NEGOTIATING`, `AUTHENTICATING`,
`ACTIVE`, `CLOSING`, `CLOSED`. Session-state vocabulary: `none`, `active`,
`unchanged`, `terminated_normally`, `terminated_abnormally`, `withdrawn`.

Error codes use the `proto/syntra/v1/errors.proto` enum names
(`UNAUTHENTICATED`, `RESOURCE_EXHAUSTED`, …). `message_pattern` is a
case-insensitive substring that MUST appear (for generic-text checks) or a
`NEGATIVE:` list of substrings that MUST NOT appear (for hygiene checks).

## Base64 and hex conventions

- `*_b64` fields are RFC 4648 §4 standard-alphabet base64 of exact bytes.
- `*_hex` fields are lowercase hex without prefixes or separators, except
  where a vector table uses space-separated groups for readability (runners
  MUST strip whitespace before decoding).
- `payload_b64: ""` (empty string) is a meaningful empty payload, distinct
  from an absent `payload_b64` (unset outcome — always a failure).

## Schema validation

`schema.yaml` in this directory is the machine-readable schema. Validate with
any YAML parser plus the `required` / `pattern` rules stated there, for
example:

```sh
python3 scripts/validate-conformance.py conformance/manifest/*.yaml conformance/profiles.yaml
```

(The script is illustrative; any equivalent check in any language satisfies
the requirement. What matters is that the files parse and cross-reference:
every `requirement` exists in `requirements.yaml`, every `profile` exists in
`profiles.yaml`, every `vector_ref` exists in `test-vectors/`.)

In `conformance/profiles.yaml`, each `manifests` entry is either a path or
a `{path, select}` map that filters by exact field equality (for example
`select: {mandatory: true, capabilities: []}` selects only mandatory
capability-free cases; see `conformance/README.md` §2.1).

## Manifest index

RFC 0007 is accepted. `sc1-wss.yaml` registers the `SNTR-SC1-WSS-V1` cases
against `SNTR-SCW-*`, `SNTR-SC-*` and `SNTR-DAUTH-*`. The companion
[`../plans/secure-channel.md`](../plans/secure-channel.md) retains historical
manual-observation mapping. Registration is not execution: no `CONF-SCW-*`
verdict is claimed, and implementation tests are not a substitute for the
registered cases. Lifecycle rows whose host transaction is not implemented
remain manual in `requirements.yaml` rather than being marked automated.

| File | Cases | Section |
|---|---|---|
| `core.yaml` | CONF-CORE-001…010 | §E valid/invalid envelope, unknown field/enum, version, capability, ordering, protocol error, close |
| `session.yaml` | CONF-SESS-001…010 + CONF-SESS-R01 (Optional resume-accept) | §F |
| `rpc.yaml` | CONF-RPC-001…012 | §G |
| `events.yaml` | CONF-EVT-001…015 | §H (Optional rows gated) |
| `transport-tcp.yaml` | CONF-TCP-001…008 | §I TCP |
| `transport-tls.yaml` | CONF-TLS-001…004 | §I TLS |
| `transport-http.yaml` | CONF-HTTP-001…018 | §I HTTP/1.1 |
| `transport-https.yaml` | CONF-HTTPS-001…014 | §I HTTPS/H1 + H2 |
| `transport-ws.yaml` | CONF-WS-001…017 | §I WS |
| `transport-wss.yaml` | CONF-WSS-001…010 | §I WSS |
| `security.yaml` | CONF-SEC-001…011 | §Q negative cases (STEST-001…011) |
| `requirements.yaml` | SNTR-* → test traceability | §D |
