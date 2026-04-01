#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/jiachen03/Documents/Paper/ai-paper-daily"
cd "$ROOT"

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

python -m app.main run-once
