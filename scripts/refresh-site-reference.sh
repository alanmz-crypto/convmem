#!/usr/bin/env bash
# refresh-site-reference.sh — regenerate the site-reference index

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir/.."

bash scripts/generate-site-reference.sh
bash scripts/verify-site-reference.sh
