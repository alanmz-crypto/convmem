#!/usr/bin/env bash
# extract-builder-reference.sh — stage pdftotext slices for builder-reference digests
#
# Writes raw text extracts to staging/builder-reference/ (gitignored).

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

STAGING="staging/builder-reference"
mkdir -p "$STAGING"

extract_range() {
  local pdf="$1"
  local start="$2"
  local end="$3"
  local out="$4"
  pdftotext -f "$start" -l "$end" -layout "$pdf" "$out"
}

extract_range \
  "/home/lauer/Documents/Computing/Projects/Convmem/SuggestedBooksClaude/APhilosiphyOfSoftwareDesign.pdf" \
  34 92 \
  "$STAGING/ousterhout-34-92.txt"

extract_range \
  "/home/lauer/Documents/Computing/Projects/Convmem/SuggestedBooksChatGPT/An introduction to information retrieval -- Christopher D_ Manning; Prabhakar Raghavan; Hinrich Schütze -- 1, 2008 -- Cambridge University Press -- isbn13 9780511410802 -- 776b1e479b67f46d692cbd9ab6920478 -- Anna’s Archive.pdf" \
  100 161 \
  "$STAGING/manning-100-161.txt"

extract_range \
  "/home/lauer/Documents/Computing/Projects/Convmem/SuggestedBooksClaude/WhyProgramsFailAGuideToSystematicDebugging.pdf" \
  130 210 \
  "$STAGING/zeller-130-210.txt"

extract_range \
  "/home/lauer/Documents/Computing/Projects/Convmem/SuggestedBooksClaude/SoftwareArchitectureTheHardParts.pdf" \
  20 95 \
  "$STAGING/hard-parts-20-95.txt"

echo "Staged builder-reference extracts in $STAGING"

