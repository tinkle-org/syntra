# Conformance — update and recovery (`CONF-URP-001…009`)

Related normative requirements are cited per case; test IDs are not normative.
Neutral fixtures only: generic subscription, generic key and value read,
and echo round trip with opaque payloads.

Conformance rule for optionality: any case exercising a capability the
implementation does not advertise MUST result in `UNSUPPORTED` or `SKIP`,
never `FAIL`.

Contract terms follow [Update/Recovery Profile](../../specifications/profiles/recovery.md)
and the proposal in [RFC 0006](../../rfcs/0006-update-recovery-profile.md).
Machine-readable equivalents are in [recovery machine snippet](../manifest/recovery.yaml).
Guidance on fields is in [manifest format](../manifest/README.md).
Related event coverage is in [event conformance](../events/events.md).

Harness fault injection: `faults` keys (`emit_batches`, `skip_batch`, `emit_duplicate_event`, `flood_events`) are harness-side instrumentation that drives the host to emit, duplicate, drop, or flood batches; they are not wire fields, consistent with `emit_events`, `emit_duplicate_event`, `flood_events` precedent in [event manifest](../manifest/events.yaml).

## CONF-URP-001 mandatory-only fallback

- Related normative requirement: SNTR-CAP-003, SNTR-EVENT-001, SNTR-EVENT-011.
- Preconditions: ACTIVE; mandatory-only Host with no confirmed profile.
- Input: generic subscription invocation without confirmed capability.
- Expected output: `UNIMPLEMENTED`; no batches emitted; mandatory invocation interop unaffected.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Optional; runs against mandatory-only Hosts, where a correct `UNIMPLEMENTED` refusal reports `UNSUPPORTED` (not `SKIP`).

## CONF-URP-002 duplicate tolerance

- Related normative requirement: SNTR-EVENT-007, SNTR-REL-005.
- Preconditions: ACTIVE; subscription confirmed.
- Input: Host emits the same batch twice across the recovered and live boundary.
- Expected output: Initiator tolerates the duplicate with no violation and no error storm.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Optional, gated on `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; SKIP when unclaimed).

## CONF-URP-003 gap detection

- Related normative requirement: SNTR-EVENT-006, SNTR-EVENT-021.
- Preconditions: ACTIVE; subscription confirmed.
- Input: Host emits batches that carry predecessor and result checkpoints; one batch is withheld to form a gap.
- Expected output: Initiator detects the gap by predecessor chaining; no arithmetic on checkpoint bytes; no structural parsing.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Optional, gated on `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; SKIP when unclaimed).

## CONF-URP-004 replay paging

- Related normative requirement: SNTR-EVENT-008, SNTR-EVENT-009.
- Preconditions: ACTIVE; subscription confirmed.
- Input: replay from the last confirmed checkpoint where retained history exceeds one page.
- Expected output: bounded pages each stating the continuation marker and the catch-up boundary; never burst beyond documented bounds; Initiator follows the marker page by page and stops at the boundary.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Optional, gated on `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; SKIP when unclaimed).

## CONF-URP-005 expired continuation with snapshot-required

- Related normative requirement: SNTR-EVENT-009.
- Preconditions: ACTIVE; expired checkpoint outside retention.
- Input: replay from the expired checkpoint.
- Expected output: `FAILED_PRECONDITION` with explicit snapshot-required signal; recovery follows the snapshot path; never silent restart from an unrelated point.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Optional, gated on `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; SKIP when unclaimed).

## CONF-URP-006 snapshot install gate

- Related normative requirement: SNTR-EVENT-008.
- Preconditions: ACTIVE; subscription confirmed.
- Input: snapshot offer under a provider-proven boundary checkpoint followed by bounded transfer pages and boundary confirm.
- Expected output: installation completes only when the Initiator confirms the boundary checkpoint; later batches chain from exactly that boundary; no partial install without boundary confirm.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Optional, gated on `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; SKIP when unclaimed).

## CONF-URP-007 reconnect re-subscribe

- Related normative requirement: SNTR-SESS-008, SNTR-EVENT-020.
- Preconditions: new transport connected with no prior subscription.
- Input: new transport and handshake; attempt to receive without re-subscribing.
- Expected output: no batches arrive; Initiator re-subscribes explicitly with a fresh handle; old handle and checkpoint carry no continuity without negotiated recovery.
- Expected connection state: ACTIVE.
- Expected session state: active.
- Mandatory/optional: Optional, gated on `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; SKIP when unclaimed).

## CONF-URP-008 overflow with reject-new-work

- Related normative requirement: SNTR-EVENT-030, SNTR-REL-007.
- Preconditions: ACTIVE; subscription confirmed; bounded buffer ready for flood.
- Input: Host produces batches faster than the Initiator consumes.
- Expected output: `RESOURCE_EXHAUSTED` on new work with documented backoff (this case covers the reject-new-work outcome and runs only when the host documents that policy; `CONF-URP-009` covers the permitted continuity-loss alternative and runs only under that policy; satisfying either satisfies the overflow requirement); never unbounded queueing; never silent truncation without the documented signal.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Optional, gated on `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; SKIP when unclaimed or when the host does not document reject-new-work).

## CONF-URP-009 overflow with continuity loss

- Related normative requirement: SNTR-EVENT-030, SNTR-REL-007.
- Preconditions: ACTIVE; subscription confirmed; bounded buffer ready for flood.
- Input: Host produces batches faster than the Initiator consumes.
- Expected output: explicit continuity loss with a new generation ending only the affected stream (this case covers the continuity-loss alternative and runs only when the host documents that policy; `CONF-URP-008` covers the permitted `RESOURCE_EXHAUSTED` alternative and runs only under that policy; satisfying either satisfies the overflow requirement); never unbounded queueing; never silent truncation without the documented signal.
- Expected connection state: ACTIVE.
- Expected session state: unchanged.
- Mandatory/optional: Optional, gated on `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; SKIP when unclaimed or when the host does not document continuity-loss).

## Sequence view

```text
Initiator                              Host
    |                                     |
    |--- invocation{negotiate profile} --->|
    |<-- result{confirmed and bounds} -----|
    |--- invocation{subscribe generic} --->|
    |<-- result{opaque handle and gen} ----|
    |<-- notification{batch with           |
    |         predecessor and result} ----|
    |--- invocation{replay from checkpoint}|
    |<-- notification{page and marker} ---|
    |<-- notification{catch-up done} -----|
    |--- invocation{confirm checkpoint} -->|
    |<-- result{confirmed} ----------------|
    |<-- notification{snapshot-required} -|
    |--- invocation{snapshot offer} ----->|
    |<-- result{snapshot page and         |
    |         boundary proven} ------------|
    |--- invocation{confirm boundary} ---->|
    |<-- result{installed with new gen} ---|
```

## Traceability

| Test | Requirement family |
|---|---|
| CONF-URP-001 | CAP-003, EVENT-001/011 (mandatory-only fallback) |
| CONF-URP-002 | EVENT-007, REL-005 (duplicate tolerance) |
| CONF-URP-003 | EVENT-006/021 (gap detection) |
| CONF-URP-004 | EVENT-008/009 (replay paging) |
| CONF-URP-005 | EVENT-009 (expired continuation) |
| CONF-URP-006 | EVENT-008 (snapshot install gate) |
| CONF-URP-007 | SESS-008, EVENT-020 (reconnect) |
| CONF-URP-008 | EVENT-030, REL-007 (overflow reject-new-work) |
| CONF-URP-009 | EVENT-030, REL-007 (overflow continuity loss) |

Further detail is in [profile readme](README.md).
