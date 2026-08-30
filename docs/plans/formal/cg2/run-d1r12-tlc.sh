#!/usr/bin/env bash
set -euo pipefail
: "${TLA_JAR:?TLA_JAR must be set}"
: "${TLA_JAR_APPROVED_SHA256:?TLA_JAR_APPROVED_SHA256 must be set}"
sha="$(sha256sum "$TLA_JAR" | awk '{print $1}')"
[[ "$sha" == "$TLA_JAR_APPROVED_SHA256" ]] || {
  echo "JAR SHA-256 mismatch: found=$sha expected=$TLA_JAR_APPROVED_SHA256" >&2
  exit 1
}
cd "$(dirname "$0")/../../../.."
MODE="${1:-positive}"
echo "implementation_sha=$(git rev-parse HEAD) mode=$MODE"
if [[ "$MODE" == "positive" ]]; then
  configs=(CG2Cutover CG2StaleReconcile CG2Rename CG2DesignA)
  expect_fail=(0 0 0 0)
elif [[ "$MODE" == "negative" ]]; then
  configs=(CG2Cutover-WrongSelector CG2Cutover-CopiedServing)
  expect_fail=(1 1)
else
  echo "usage: $0 [positive|negative]" >&2
  exit 2
fi
for i in "${!configs[@]}"; do
  config="${configs[$i]}"
  expect="${expect_fail[$i]}"
  log="/tmp/tlc-${config}-$(git rev-parse HEAD).log"
  set +e
  timeout 1800 java -Xmx2g -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC \
    -workers 2 -coverage 1 \
    -config "docs/plans/formal/cg2/${config}.cfg" \
    docs/plans/formal/cg2/CG2Authority.tla >"$log" 2>&1
  status=$?
  set -e
  echo "config=${config} exit=${status} log=${log} expect_fail=${expect}"
  if [[ "$expect" -eq 0 ]]; then
    [[ "$status" -eq 0 ]] || { tail -30 "$log" >&2; exit 1; }
    rg -q "Model checking completed. No error has been found." "$log" || {
      echo "missing PASS banner in ${log}" >&2
      exit 1
    }
  else
    [[ "$status" -ne 0 ]] || { echo "expected invariant violation for ${config}" >&2; exit 1; }
    rg -q "Error: Invariant .* is violated." "$log" || {
      echo "missing invariant violation in ${log}" >&2
      exit 1
    }
  fi
done
echo "D1R12 TLC ${MODE} complete"
