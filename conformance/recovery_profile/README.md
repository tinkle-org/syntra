# Recovery profile conformance — update and recovery

Additive conformance material for the optional update and recovery contract.

The contract is described in [Update/Recovery Profile](../../specifications/profiles/recovery.md)
and proposed in [RFC 0006](../../rfcs/0006-update-recovery-profile.md).

This directory does not change mandatory behavior. It only adds optional
coverage that is evaluated when the capability is claimed.

## Files

- [recovery prose](recovery.md) — human-readable cases `CONF-URP-001…011`.
- [recovery machine snippet](../manifest/recovery.yaml) — machine-readable cases for runners.
- Related event material: [event conformance](../events/events.md).
- Manifest guidance: [manifest format](../manifest/README.md).
- Claimed profile definition: [profiles](../profiles.yaml).

## Profile and capability

- Profile: `SNTR-EVENTS-V1`.
- Capability: `syntra.update-recovery/1` (placeholder pending RFC 0006 acceptance; MUST NOT be advertised until accepted).
- Every case in [recovery machine snippet](../manifest/recovery.yaml) sets `mandatory: false`.
- Every case in [recovery machine snippet](../manifest/recovery.yaml) sets `capabilities: [syntra.update-recovery/1]`.
- Every case in [recovery machine snippet](../manifest/recovery.yaml) sets `profile: SNTR-EVENTS-V1`.

## Optionality rule

Any case exercising a capability the implementation does not advertise
MUST result in `UNSUPPORTED` or `SKIP`, never `FAIL`.

A mandatory-only implementation that correctly refuses profile use with
`UNIMPLEMENTED` satisfies `CONF-URP-001` as `UNSUPPORTED`.

## Preconditions and expected states

Preconditions use only the closed vocabulary from [manifest format](../manifest/README.md):

- `active_session`
- `subscription_confirmed`
- `cursor_expired`
- `transport_connected`
- `flood_ready`

Expected states use only the closed vocabularies for connection and session:

- Connection: `ACTIVE`.
- Session: `unchanged` or `active` for a new session after reconnect.

## Coverage

| Test | Topic |
|---|---|
| `CONF-URP-001` | Mandatory-only fallback |
| `CONF-URP-002` | Duplicate tolerance |
| `CONF-URP-003` | Gap detection |
| `CONF-URP-004` | Replay paging |
| `CONF-URP-005` | Expired continuation with snapshot-required |
| `CONF-URP-006` | Snapshot install gate |
| `CONF-URP-007` | Reconnect re-subscribe |
| `CONF-URP-008` | Overflow with reject-new-work |
| `CONF-URP-009` | Overflow with continuity loss |
| `CONF-URP-010` | Dropped-final-update silence |
| `CONF-URP-011` | Fixed-boundary replay |

Details are in [recovery prose](recovery.md). Neutral fixtures only:
generic subscription, generic key and value read, and echo round trip.
