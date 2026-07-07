#!/usr/bin/env bash
# Run the full model-quality scorecard: doctor (incl. summarization canary),
# then the three evals. Surfaces a distinct signal when BOTH local-model evals
# (summaries + synthesis) regress on the same run — since the summarizer and the
# local synthesis fallback are the same weights (llama3.1:8b), that points at a
# model/infra root cause rather than a prompt/fixture issue.
#
# Usage: scripts/eval-all.sh [--judge]
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${CONVMEM_PY:-python3}"
JUDGE=""
[[ "${1:-}" == "--judge" ]] && JUDGE="--judge"

# eval_provenance exit codes: 0 ok, 1 genuine regression, 3 needs rebaseline.
EXIT_REGRESSION=1

echo "== doctor =="
"$PY" -m convmem doctor
DOCTOR_RC=$?

echo
echo "== retrieval =="
"$PY" "$REPO/scripts/eval-retrieval.py"
RETRIEVAL_RC=$?

echo
echo "== summaries =="
"$PY" "$REPO/scripts/eval-summaries.py" $JUDGE
SUMMARIES_RC=$?

echo
echo "== synthesis =="
"$PY" "$REPO/scripts/eval-synthesis.py" $JUDGE
SYNTHESIS_RC=$?

echo
echo "== scorecard =="
printf '  %-12s exit=%s\n' "doctor" "$DOCTOR_RC"
printf '  %-12s exit=%s\n' "retrieval" "$RETRIEVAL_RC"
printf '  %-12s exit=%s\n' "summaries" "$SUMMARIES_RC"
printf '  %-12s exit=%s\n' "synthesis" "$SYNTHESIS_RC"

echo
if [[ "$SUMMARIES_RC" -eq "$EXIT_REGRESSION" && "$SYNTHESIS_RC" -eq "$EXIT_REGRESSION" ]]; then
  echo "SIGNAL: shared local-model root cause — both local-model evals regressed"
  echo "        (summarizer == local synth fallback == llama3.1:8b). Investigate"
  echo "        model file / Ollama / GPU, not prompts. Check 'doctor' canary latency."
elif [[ "$SUMMARIES_RC" -eq "$EXIT_REGRESSION" || "$SYNTHESIS_RC" -eq "$EXIT_REGRESSION" ]]; then
  echo "SIGNAL: single-eval regression — likely prompt/fixture-level for that path."
fi

# Overall exit: worst of the eval codes (doctor is informational here).
OVERALL=0
for rc in "$RETRIEVAL_RC" "$SUMMARIES_RC" "$SYNTHESIS_RC"; do
  [[ "$rc" -gt "$OVERALL" ]] && OVERALL="$rc"
done
exit "$OVERALL"
