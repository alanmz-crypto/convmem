#!/usr/bin/env bash
# CG-2 Design A TLC runner — implements EXECUTION-cg2-design-a.md §11.4–§11.5.
# Do not run until Ryan approves TLA_JAR_APPROVED_SHA256.
set -euo pipefail

: "${TLA_JAR:?TLA_JAR must be set to absolute readable path to approved tla2tools.jar}"
test -r "$TLA_JAR" || { echo "D6 STOP: TLA_JAR not readable: $TLA_JAR" >&2; exit 1; }

TLA_JAR_SHA256="$(sha256sum "$TLA_JAR" | awk '{print $1}')"
TLC_VERSION="$(java -cp "$TLA_JAR" tlc2.TLC -version 2>&1 | tr -d '\r')"
JAVA_VERSION="$(java -version 2>&1 | head -n1 | tr -d '\r')"

: "${TLA_JAR_APPROVED_SHA256:?approved JAR digest required in Execute evidence input}"
if [[ "$TLA_JAR_SHA256" != "$TLA_JAR_APPROVED_SHA256" ]]; then
  echo "D6 STOP: TLA_JAR SHA-256 mismatch" >&2
  echo "  found:    $TLA_JAR_SHA256" >&2
  echo "  approved: $TLA_JAR_APPROVED_SHA256" >&2
  exit 1
fi

TLA_TIMEOUT_SECONDS=1800
TLA_MODULE="docs/plans/formal/cg2/CG2Authority.tla"
TLC_JAVA_OPTS=(-Xmx2g -XX:+UseParallelGC)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "TLA_JAR=$TLA_JAR"
echo "TLA_JAR_SHA256=$TLA_JAR_SHA256"
echo "TLC_VERSION=$TLC_VERSION"
echo "JAVA_VERSION=$JAVA_VERSION"
echo "implementation_sha=$(git rev-parse HEAD)"

for config in CG2Cutover CG2StaleReconcile CG2Rename CG2DesignA; do
  cfg_path="docs/plans/formal/cg2/${config}.cfg"
  test -r "$cfg_path" || { echo "D6 STOP: missing config $cfg_path" >&2; exit 1; }

  log_path="/tmp/tlc-${config}-$(git rev-parse HEAD).log"
  cmd=(
    timeout "${TLA_TIMEOUT_SECONDS}"
    java "${TLC_JAVA_OPTS[@]}"
    -cp "$TLA_JAR" tlc2.TLC
    -workers 2 -coverage 1
    -config "$cfg_path"
    "$TLA_MODULE"
  )

  start_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  set +e
  "${cmd[@]}" >"$log_path" 2>&1
  exit_status=$?
  set -e
  end_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  echo "config=$config start=$start_ts end=$end_ts exit=$exit_status log=$log_path"

  if [[ $exit_status -eq 124 ]]; then
    echo "D6 STOP: TLC timeout for ${config} after ${TLA_TIMEOUT_SECONDS}s" >&2
    exit 1
  fi
  if [[ $exit_status -ne 0 ]]; then
    echo "D6 STOP: TLC non-zero exit for ${config}: ${exit_status}" >&2
    exit 1
  fi
  if [[ ! -s "$log_path" ]]; then
    echo "D6 STOP: TLC produced no output for ${config}" >&2
    exit 1
  fi
done

echo "D6 TLC: all four configurations completed with exit 0"
