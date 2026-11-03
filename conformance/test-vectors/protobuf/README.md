# Golden Protobuf vectors

Known valid encodings for every v1 core message, verified with
`protoc --decode=syntra.v1.Frame` against `proto/syntra/v1/*.proto`.

- [`vectors.yaml`](vectors.yaml) — machine-readable: human representation,
  serialized hex, and expected semantic fields per vector.
- Bodies and error outcomes use the names in the current IDL. Authentication
  fixtures isolate opaque credential carriage, not a separate wire message.

Critical rule (SNTR-SER-002/901): these vectors assert **logical equality**
(decoded fields), never byte-identical re-emission. A conforming implementation
MUST accept field-reordered and unknown-field-bearing equivalents
(`GOLD-PROT-UNKNOWN-FIELD-01` proves tolerance). The authenticated inner prefix
(`test-vectors/tcp/`) plus a chosen fixture payload is byte-exact — and only
for that fixture.
