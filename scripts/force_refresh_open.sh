#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/jiachen03/ai-paper-daily-runtime"
cd "$ROOT"

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

ensure_web() {
  if curl -fsS --max-time 2 http://127.0.0.1:8000 >/dev/null 2>&1; then
    return 0
  fi

  nohup python -m app.main web >> "$ROOT/logs/manual-web.log" 2>&1 &

  for _ in {1..15}; do
    if curl -fsS --max-time 2 http://127.0.0.1:8000 >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  return 1
}

python -m app.main run-once
if ensure_web; then
  TODAY=$(date +%F)
  TS=$(date +%Y%m%d%H%M%S)
  open "http://127.0.0.1:8000/?date=${TODAY}&ts=${TS}"
else
  echo "[ERROR] Web server did not become ready on http://127.0.0.1:8000"
  exit 1
fi
