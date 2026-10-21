#!/usr/bin/env sh
# Collect Syntra v1 release-candidate artifacts into dist/release/<name>/.
# Repository tooling only: assembles files and checksums. It NEVER creates
# git tags and NEVER publishes anything (no crates.io publish, no GitHub
# Release). Tagging and publication are maintainer actions gated by
# RELEASE.md §4 (release-plz + release.yml).
#
# Usage: sh scripts/collect-release-artifacts.sh syntra-core-v1.0.0-rc.1 [git-ref]
#   or:  sh scripts/collect-release-artifacts.sh v1.0.0-rc.1 syntra-core-v1.0.0-rc.1
#   <name>    artifact directory name (e.g. syntra-core-v1.0.0-rc.1, or bare
#             v1.0.0-rc.1 for a version-named directory); must match
#             (syntra-core-)vX.Y.Z[-rc.N]
#   [git-ref] optional revision to materialize (default: refs/tags/<name> when
#             <name> is a syntra-core-v… tag, else refs/tags/syntra-core-<name>).
#             The ref is checked out to a temporary worktree; the current
#             checkout and all tags are left untouched.
set -eu

NAME="${1:?usage: sh scripts/collect-release-artifacts.sh syntra-core-v1.0.0-rc.1 [git-ref]}"

case "$NAME" in
  syntra-core-v[0-9]*.[0-9]*.[0-9]*|syntra-core-v[0-9]*.[0-9]*.[0-9]*-rc.[0-9]*|v[0-9]*.[0-9]*.[0-9]*|v[0-9]*.[0-9]*.[0-9]*-rc.[0-9]*)
    ;;
  *)
    echo "error: name must look like syntra-core-v1.0.0 or syntra-core-v1.0.0-rc.1 (bare v1.0.0… accepted with explicit syntra-core-v… ref), got: $NAME" >&2
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
elif case "$NAME" in syntra-core-*) false;; v*) true;; *) false;; esac && git -C "$ROOT" show-ref --verify --quiet "refs/tags/syntra-core-$NAME"; then
  REF="refs/tags/syntra-core-$NAME"
else
  echo "error: tag refs/tags/$NAME does not exist; supply an explicit syntra-core-v… git-ref" >&2
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
echo "NOTE: artifacts assembled only. Tagging (RELEASE.md §4) and crates.io"
echo "publication via release-plz remain maintainer actions."
