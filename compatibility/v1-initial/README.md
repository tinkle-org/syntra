# Initial schema-layout baseline (not a release)

Baseline identifier: `v1-initial`, established 2026-10-19. `image.json` is
the first seven-file layout snapshot (originally a candidate), built with Buf **1.59.0**, without
source locations. It is an actual initial snapshot, not a fabricated prior
version or tagged release. Its SHA-256 is recorded in `manifest.json`.
It gates subsequent `proto/syntra/v1` changes under Buf `FILE` and remains
unchanged by the removal of the old schema tree. `proto/syntra/v1` is now
the sole source of truth by explicit user direction, recorded in RFC 0001
B9. The snapshot does not erase the known historical FILE/source break or
establish formal maintainer/RFC approval of unresolved behavior.

`historical.json` is an immutable FileDescriptorSet generated before removal
from the actual unchanged historical sources at commit
`92e5f281aa7c3adac9ba78588c1140b12d55c1d9`:
[session.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/session.proto)
and [error.proto](https://github.com/tinklehq/syntra/blob/92e5f281aa7c3adac9ba78588c1140b12d55c1d9/schema/syntra/v1/error.proto).
`manifest.json` retains `historical_sources` path/hash provenance and adds
`historical_image_sha256` for this archive. Those source paths are historical
identities, not live repository files. Validation checks the archived
descriptor hash and compares every historical declaration, including
reservations and scalar presence. Historical `FILE` failures are expected
and asserted as known source-breaking differences, not pending layout approval
or suppressed checks in `buf.yaml`.

Run from the repository root:

```sh
buf breaking --against compatibility/v1-initial/image.json
python3 -m unittest discover -s tests/schema -p 'test_*.py' -v
```

The test runner reads `historical.json` directly, runs the separate historical
WIRE audit, and verifies that FILE reports the owning-file changes. It needs
neither a Git checkout nor a duplicate source tree, and never edits either
descriptor archive. The updated descriptor/tooling suite has 13 checks
(the original 12 plus a sole-source regression check); post-deletion results
are pending in the [validation record](../../specifications/schema/validation.md).

To reproduce this initial image **only at its reviewed source snapshot**:

```sh
buf build --as-file-descriptor-set --exclude-source-info \
  -o compatibility/v1-initial/image.json
shasum -a 256 compatibility/v1-initial/image.json
```

Do not run that command to make a breaking edit pass. A future baseline
gets a new directory, provenance, review, and compatibility analysis. At
the first accepted release, use the real release tag/image as the next
baseline; do not invent a predecessor release or create tags from tooling.
