# Public Protobuf IDL

- [Reference and requirement mapping](reference.md)
- [Pinned generation and validation](generation.md)
- [Wire/source/behavior compatibility](compatibility.md)
- [Executed validation results and acceptance gaps](validation.md)
- [Initial baseline and archived historical descriptors](../../compatibility/v1-initial/README.md)
- [RFC 0001: recorded layout decision and remaining blockers](../../rfcs/0001-public-idl-layout.md)

The eight files under `proto/syntra/v1` — including `recovery_profile.proto`,
added for the accepted [RFC 0006](../../rfcs/0006-update-recovery-profile.md)
§11 update/recovery profile (profile payload declarations only) — are the sole
Protobuf source of truth by explicit user direction. The old `schema/syntra/v1`
tree is removed; historical declarations survive in the immutable
compatibility archive. The files represent the existing contract;
`session.proto` and `capabilities.proto` are deliberately documentation-only,
not speculative messages. The requested extensions/renames were resolved by
the acceptance wave (accepted [RFC 0001](../../rfcs/0001-public-idl-layout.md)):
the raw-wire classification items are specified by accepted
[RFC 0008](../../rfcs/0008-mobile-lifecycle-and-v1-acceptance.md) D1 (reserved
tags 16/17 rejected, 18..31 reserved for future bodies), and the remaining
extensions/renames stay deferred per the retained B11 deferral table (see the
[A–G matrix](reference.md#delivered-versus-blocked-ag-coverage)). RFC 0001 B9
records the implemented layout decision and the known FILE/source break;
approval authority is recorded by the acceptance decision records, and no
runtime execution is claimed here.
