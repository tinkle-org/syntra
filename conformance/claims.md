# Conformance claim wording (Section P)

These rules are normative for any public statement that cites this suite.
A technically passing run with non-conformant wording is a non-conformant claim.

## Allowed forms

- Single secure transport:

  > "Conforms to Syntra Core v1 and WSS/H1 v1"

- Two secure transports:

  > "Conforms to Syntra Core v1 with transports WSS/H1 v1, HTTPS/H2 v1"

- With the (future) event capability, replay explicitly scoped:

  > "Conforms to Syntra Core v1 with transports WSS/H1 v1, HTTPS/H2 v1 and
  > capability events-v1 (replay excluded)"

- Mandatory-only host (no event support — this is conformant):

  > "Conforms to Syntra Core v1 (mandatory-only; event subscriptions correctly
  > declined with UNIMPLEMENTED) over TLS/TCP v1"

## Forbidden forms

- Bare "Syntra compliant", "Syntra certified", "Syntra compatible",
  "Syntra-conformant", or any wording that omits the profile list.
- "Syntra Core" without the version (`v1`).
- Naming a capability (`events-v1`, `events-replay-v1`, `resume-v1`) without
  its RFC reference, or before its RFC is accepted.
- Implying production readiness from a development-only transport.

## Development-only suffix rule

Any claim naming `SNTR-TCP-V1`, `SNTR-HTTP-V1`, or `SNTR-WS-V1` MUST append:

> "(restricted development only; not for public production traffic)"

Example:

> "Conforms to Syntra Core v1 over TCP v1 (restricted development only;
> not for public production traffic)"

## Placement rules

- The declaration (`declaration.example.yaml`) lists exact profile IDs
  (`SNTR-WSS-H1-V1`), per-case verdicts, bounds, and log references.
- Marketing pages, READMEs, and datasheets MUST use the §Allowed-forms prose
  and link the declaration.
- Capability exclusions MUST be stated ("replay excluded") rather than left
  ambiguous. Silence about replay means replay was not evaluated, not that it
  passed.
