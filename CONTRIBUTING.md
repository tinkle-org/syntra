# Contributing to Syntra

Thank you for helping make Syntra an independent, specification-first
protocol. This guide explains how to propose changes, how RFCs are
reviewed, and what bars apply.

Related: [`GOVERNANCE.md`](GOVERNANCE.md) (who approves what),
[`rfcs/README.md`](rfcs/README.md) (RFC lifecycle),
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md),
[`SECURITY.md`](SECURITY.md).

## 1. Ground rules

1. **Specifications first.** Normative behavior lives in Markdown specs
   and `.proto` files, not in code. Do not add behavior only in an
   implementation.
2. **Independent and generic.** Do not reference any private product,
   company infrastructure, messenger, social platform, payment system,
   proprietary server, database, cloud deployment, or unpublished
   architecture. Do not add domain types such as chat messages,
   conversations, contacts, profiles, or receipts. Generic principals,
   endpoints, identities, opaque payloads, requests, responses, streams,
   and events are the allowed abstractions.
3. **No custom crypto.** Do not propose application-level encryption,
   ratchets, or custom ciphers. Syntra MAY carry opaque encrypted bytes
   but MUST NOT parse or decrypt them.
4. **Examples stay neutral.** Use `echo`, generic key/value, or generic
   event subscriptions.
5. **Small, auditable changes.** Prefer narrow PRs. One RFC per change.
6. **Code of Conduct applies** in all spaces.

## 2. Ways to contribute

- **Fixes to non-normative text** (typos, clarifications with no
  behavioral change): direct PR.
- **Normative changes** (any MUST/SHOULD, wire field, state machine,
  error code, transport mapping, security requirement): **RFC required.**
  Open an RFC per `rfcs/README.md` before or alongside the PR.
- **Schemas (`proto/syntra/v1/*.proto`)**: RFC required for any field change.
  Run Buf lint + breaking-change detection (see Sec. 5).
- **Conformance tests and fixtures** (`conformance/`): encouraged with
  every normative PR. Use deterministic fixtures. Protocol behavior
  changes go under `specifications/`; conformance changes go under
  `conformance/`.
- **Docs and examples**: welcome; must stay generic per Sec. 1.
- **Generated language types**: committed under `crates/` (Rust prost
  output) and `bindings/go/` (Go protobuf output, incl. `*.pb.go`) — no
  `gen/`, `generated/`, or `bindings/` roots outside `bindings/go/`, no
  tracked `.tmp/` output. Regenerate with the pinned template and commit
  the result in the same PR (`scripts/validate-schema.py --drift-only`
  must stay green; the repository-boundary check,
  `scripts/validate-repo.py boundary`, fails on legacy trees, tracked
  `.tmp/`, or drift). Consumers use the committed tree or the GitHub
  Release assets (see `docs/schema-registry.md`); there is no registry
  publication.

## 3. Proposing a change

1. Search existing [Issues](https://github.com/tinklehq/syntra/issues)
   and [RFCs](https://github.com/tinklehq/syntra/pulls) (use the `rfc`
   label where applied) to avoid duplicates.
2. For normative work: copy `rfcs/template.md` to
   `rfcs/NNNN-short-title.md` (see `rfcs/README.md`) and open a PR
   marked as RFC. Explain motivation, normative diff, alternatives,
   compatibility, security, and test plan.
3. Implement the spec/schema diff in the same PR or a linked PR.
   Cross-reference both.
4. Ensure every new MUST/MUST NOT has:
   - a requirement ID (e.g., `SYN-HS-014`),
   - separate client and server obligations where applicable,
   - success + failure transitions,
   - an example or sequence diagram where behavior is involved,
   - security and compatibility notes,
   - acceptance criteria and a conformance test link (or a tracked
     placeholder issue if the suite does not yet cover it).
5. Sign off your commits (see Sec. 6).

## 4. RFC review and acceptance

Full lifecycle: [`rfcs/README.md`](rfcs/README.md).

Summary:

- Discussion happens on the RFC PR. Maintainers assign reviewers with
  protocol and security perspective.
- **Non-normative** changes: one maintainer approval may merge.
- **Normative** changes: REQUIRE maintainer approval per
  [`GOVERNANCE.md`](GOVERNANCE.md) Sec. 3 (quorum, no unresolved
  normative objection, security review for security-adjacent changes).
- **Breaking (wire-incompatible) changes**: REQUIRE an accepted major-
  version RFC, migration notes, and a `CHANGELOG.md` entry. See
  `GOVERNANCE.md` Sec. 4.
- A protocol release becomes stable only per `GOVERNANCE.md` Sec. 5
  (all normative specs + schemas + conformance suite green + tagged
  release notes).

## 5. Development checks

Before requesting review:

- [ ] Run `python3 scripts/validate-schema.py` for schema changes
      (Buf v2 STANDARD/FILE; do not weaken checks to pass). The initial FILE
      baseline is `compatibility/v1-initial/image.json`. RFC 0001 records
      the user-directed layout decision and separate, known historical
      FILE/source break. Historical comparisons read the hash-verified
      `compatibility/v1-initial/historical.json` archive, without a Git
      checkout or duplicate schema tree. Regenerate committed types in the
       same PR (`--drift-only` must pass); `cargo test` (`--workspace`
       plus `-p syntra-ffi --features test-fixture`, `-p syntra-ffi
       --features production`, and `build_contract.py`), `go test`
       (default tags plus `-tags syntranative` against the production
       library), and WASM checks (non-FFI success plus expected
       `syntra-ffi does not support WASM` failure; no browser WASM
       archive) run in CI (see `repo-validation.yml`).
- [ ] Markdown uses BCP 14 keywords correctly (capitalized only for
      normative force).
- [ ] No private dependency or domain-specific term introduced
      (`grep -ri` for product names, chat/contact/receipt terms).
- [ ] Requirement IDs unique and indexed in the changed spec.
- [ ] Proto comments match spec prose; `reserved` values untouched.
- [ ] Tests or fixtures added/updated; negative tests included for
      failures, timeouts, cancellation, oversized frames, unknown
      fields/messages, unauthenticated access.
- [ ] No `unsafe` (Rust, when present) without documented, reviewed
      justification; no panics on untrusted input; bounds checked.
- [ ] `CHANGELOG.md` updated under `Unreleased` for user-visible changes.

Schema/codec commands and pins are in `specifications/schema/generation.md`;
`proto/syntra/v1` is the sole source of truth; the old schema tree is removed.
The runtime conformance harness is still forthcoming. Never report tests as passed unless executed;
paste command + result summary in the PR.

## 6. Sign-off (DCO)

All commits REQUIRE a `Signed-off-by` trailer to certify the Developer
Certificate of Origin (DCO 1.1):

```text
Signed-off-by: Your Name <you@example.com>
```

Use `git commit -s`. By signing off you certify you have the right to
contribute the change under the project's license (Apache-2.0, see
`LICENSE` and `GOVERNANCE.md` Sec. 7) and that the contribution
follows this guide.

## 7. Style

- Specifications: RFC-style Markdown, BCP 14 keywords, requirement IDs,
  client/server obligations separated, diagrams in fenced `text` blocks.
- Protobuf: `proto3`, `package syntra.v1`, explicit field numbers,
  `reserved` preserved, comments starting with the field's contract.
- Rust (when present): `cargo fmt`, `cargo clippy -D warnings`, minimal
  dependencies, no private registries.

## 8. What not to do

- Do not invent contact addresses, endpoints, or credentials in docs.
- Do not select a different license on behalf of maintainers (project is
  Apache-2.0; see `LICENSE` and `GOVERNANCE.md` Sec. 7).
- Do not resolve wire-compat or security questions by implementation
  choice alone — open an RFC or record a blocker.
- Do not delete or silently rewrite working code; propose migration in
  `MIGRATION.md` style (inventory → classification → plan), except for the
  explicit user-directed sole-source IDL migration recorded in `MIGRATION.md`
  Sec. 8 and RFC 0001 B9.

Questions? See [`SUPPORT.md`](SUPPORT.md). For vulnerabilities, see
[`SECURITY.md`](SECURITY.md) — never file public issues for them.
