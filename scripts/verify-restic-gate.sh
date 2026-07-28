#!/usr/bin/env bash
# Manual + CI verification for Restic live-write gate (happy path + fail-closed negative).
set -euo pipefail

CONVMEM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$CONVMEM_ROOT/scripts/restic-ensure-chroma-snapshot.sh"
WRAPPER="$CONVMEM_ROOT/scripts/convmem-live-write.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FAKE_CONVMEM="$TMP/bin/convmem"
mkdir -p "$TMP/bin" "$TMP/data-root/chroma" "$TMP/repo" "$TMP/cache"
cat > "$FAKE_CONVMEM" <<'EOF'
#!/usr/bin/env bash
echo "FAKE_CONVMEM_CALLED $*"
exit 0
EOF
chmod +x "$FAKE_CONVMEM"

PASS_FILE="$TMP/restic.password"
echo "test-password-verify-gate" > "$PASS_FILE"
chmod 600 "$PASS_FILE"

ENV_FILE="$TMP/restic.env"
cat > "$ENV_FILE" <<EOF
CONVMEM_BACKUP_PROFILE=complete-data-v2
CONVMEM_DATA_ROOT=$TMP/data-root
RESTIC_REPOSITORY=$TMP/repo
RESTIC_PASSWORD_FILE=$PASS_FILE
CONVMEM_CHROMA_DIR=$TMP/data-root/chroma
RESTIC_CACHE_DIR=$TMP/cache
EOF

export CONVMEM_RESTIC_ENV="$ENV_FILE"
export PATH="$TMP/bin:$PATH"
export RESTIC_CACHE_DIR="$TMP/cache"

echo "== 4a happy path: ensure + require-current =="
echo "seed" > "$TMP/data-root/chroma/seed.txt"
echo "data" > "$TMP/data-root/seed.txt"
"$GATE" || { echo "FAIL: ensure after init"; exit 1; }
"$GATE" --require-current || { echo "FAIL: require-current after backup"; exit 1; }
"$WRAPPER" record --list | grep -q FAKE_CONVMEM_CALLED || { echo "FAIL: wrapper did not reach convmem"; exit 1; }
echo "PASS 4a"

echo "== 4b negative: missing password blocks live write (fail-closed) =="
BAD_ENV="$TMP/restic.bad.env"
cat > "$BAD_ENV" <<EOF
CONVMEM_BACKUP_PROFILE=complete-data-v2
CONVMEM_DATA_ROOT=$TMP/data-root
RESTIC_REPOSITORY=$TMP/repo
RESTIC_PASSWORD_FILE=$TMP/missing-password-file
CONVMEM_CHROMA_DIR=$TMP/data-root/chroma
RESTIC_CACHE_DIR=$TMP/cache
EOF
export CONVMEM_RESTIC_ENV="$BAD_ENV"
if "$WRAPPER" record --list 2>/dev/null; then
  echo "FAIL: wrapper should have blocked on missing password file"
  exit 1
fi
if "$WRAPPER" record --list 2>&1 | grep -q FAKE_CONVMEM_CALLED; then
  echo "FAIL: convmem was called despite gate failure"
  exit 1
fi
echo "PASS 4b"

echo "verify-restic-gate: all checks passed"
