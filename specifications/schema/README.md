# Public Protobuf IDL

- [Reference and requirement mapping](reference.md)
- [Pinned generation and validation](generation.md)
- [Wire/source/behavior compatibility](compatibility.md)
- [Executed validation results and acceptance gaps](validation.md)
- [Initial baseline and archived historical descriptors](../../compatibility/v1-initial/README.md)
- [RFC 0001: recorded layout decision and remaining blockers](../../rfcs/0001-public-idl-layout.md)

The seven files under `proto/syntra/v1` are the sole Protobuf source of
truth by explicit user direction. The old `schema/syntra/v1` tree is removed;
historical declarations survive in the immutable compatibility archive.
The files represent the existing contract; `session.proto` and `capabilities.proto`
are deliberately documentation-only, not speculative messages. Requested
extensions/renames remain blocked by the current specifications. RFC 0001
B9 records the implemented layout decision and known FILE/source break;
formal maintainer quorum and behavioral RFC approval are not claimed.
