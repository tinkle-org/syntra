# Conformance fixture guide

Deterministic, implementation-neutral inputs for the [test suite](../README.md).
Methods and payloads are neutral echo/key-value/subscription fixtures; credentials
are throwaway. No production keys or endpoints belong here.

| Directory | Inputs | Assertion layer |
|---|---|---|
| [`protobuf/`](protobuf/) | Hex and semantic fields for core messages | Decoded logical equality, not encoder byte equality |
| [`tcp/`](tcp/) | u32BE length plus chosen Frame bytes | Authenticated inner stream on every carrier; not outer TCP framing |
| [`connection/`](connection/) | Current context/prologue JSON/YAML pair and rejection recipes | Exact public encoding; no Noise ciphertext or cryptographic verdict |

Base64 uses the RFC 4648 standard alphabet. Hex has no prefix/separators;
strip whitespace in grouped displays. Fixture IDs resolve to the retained files.
The chosen inner prefix/payload and context encodings may be byte-exact without
freezing general Protobuf serialization order. No frozen TLS exchange is needed;
certificate cases reference harness-owned test PKI identities in the manifests.

Run `python3 scripts/validate-repo.py vectors` and
`python3 scripts/migrate-conformance-1.0.py` from the repository root to check
consistency and context-pair drift. Neither command executes peer behavior.
