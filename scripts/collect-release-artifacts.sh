#!/usr/bin/env sh
# Collect Syntra v1 release-candidate artifacts into dist/release/<name>/.
# Repository tooling only: assembles files and checksums. It NEVER creates
# git tags, NEVER pushes to BSR, and NEVER publishes anything. Tagging and
# publication are manual maintainer actions gated by RELEASE.md and the
# bsr-publish environment.
#
# Usage: sh scripts/collect-release-artifacts.sh v1.0.0-rc.1 [git-ref]
#   <name>    artifact directory name (e.g. v1.0.0-rc.1); must match vX.Y.Z[-rc.N]
#   [git-ref] optional revision to materialize (default: refs/tags/<name>,
#             which must exist). The ref is
#             checked out to a temporary worktree; the current checkout and
#             all tags are left untouched.
set -eu

NAME="${1:?usage: sh scripts/collect-release-artifacts.sh v1.0.0-rc.1 [git-ref]}"

case "$NAME" in
  v[0-9]*.[0-9]*.[0-9]*|v[0-9]*.[0-9]*.[0-9]*-rc.[0-9]*)
    ;;
  *)
    echo "error: name must look like v1.0.0 or v1.0.0-rc.1, got: $NAME" >&2
    exit 1
    ;;
esac

command -v buf >/dev/null 2>&1 || { echo "error: buf 1.59.0 required (see specifications/schema/generation.md)" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "error: git required" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$#" -ge 2 ]; then
  REF="$2"
elif git -C "$ROOT" show-ref --verify --quiet "refs/tags/$NAME"; then
  REF="refs/tags/$NAME"
else
  echo "error: tag refs/tags/$NAME does not exist; supply an explicit git-ref to override" >&2
  exit 1
fi
OUT="$ROOT/dist/release/$NAME"

if [ -e "$OUT" ]; then
  echo "error: $OUT already exists; remove it explicitly to rebuild" >&2
  exit 1
fi

WORK="$(mktemp -d)"
cleanup() { git -C "$ROOT" worktree remove --force "$WORK" 2>/dev/null || rm -rf "$WORK"; }
trap 'cleanup' EXIT INT TERM
git -C "$ROOT" worktree add --detach "$WORK" "$REF" >/dev/null 2>&1

mkdir -p "$OUT/descriptor" "$OUT/manifests" "$OUT/test-vectors"
(
  cd "$WORK"
  buf build -o "$OUT/descriptor/image.json"
  buf export -o "$OUT/descriptor/proto"
)
cp "$WORK/conformance/manifest/"*.yaml "$OUT/manifests/"
cp -r "$WORK/conformance/test-vectors/." "$OUT/test-vectors/"
for f in CHANGELOG.md RELEASE.md GOVERNANCE.md SESSION-OPEN-QUESTIONS.md; do
  cp "$WORK/$f" "$OUT/"
done
git -C "$ROOT" worktree remove --force "$WORK"
trap - EXIT INT TERM
# NOTE: artifacts must be built from a committed tag/commit, never from a
# dirty working tree. If buf fails here, the ref predates the current source
# layout or is otherwise not release material — fix forward, never patch.

(
  cd "$OUT"
  find . -type f ! -name SHA256SUMS -exec shasum -a 256 {} + | LC_ALL=C sort -k 2 > SHA256SUMS
)

echo "assembled $OUT"
echo "files: $(find "$OUT" -type f | wc -l | tr -d ' ')"
cat "$OUT/SHA256SUMS"
echo "NOTE: artifacts assembled only. Tagging (RELEASE.md §4) and BSR publication"
echo "(schema-publish.yml, gated) remain manual maintainer actions."
