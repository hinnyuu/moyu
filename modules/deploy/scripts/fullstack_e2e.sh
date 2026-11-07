#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMP="$(mktemp -d)"
PORT="${MOYU_E2E_PORT:-8800}"
API_LOG="$TMP/api.log"
WORKER_LOG="$TMP/worker.log"
API_PID=""
WORKER_PID=""

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "--- api.log ---"; tail -80 "$API_LOG" || true
    echo "--- worker.log ---"; tail -80 "$WORKER_LOG" || true
  fi
  [ -n "$API_PID" ] && kill "$API_PID" >/dev/null 2>&1 || true
  [ -n "$WORKER_PID" ] && kill "$WORKER_PID" >/dev/null 2>&1 || true
  wait >/dev/null 2>&1 || true
  rm -rf "$TMP"
  exit "$status"
}
trap cleanup EXIT

mkdir -p "$TMP/config" "$TMP/data" "$TMP/secrets"
echo e2e-boot-token > "$TMP/secrets/bootstrap_token"
PYTHONPATH="$ROOT/modules/config/src" python3 - "$TMP" "$ROOT" <<'PY'
import sys
from pathlib import Path
from moyu_config import ConfigProvider
base = Path(sys.argv[1])
root = Path(sys.argv[2])
provider = ConfigProvider(base / "config")
eff = provider.load()
provider.write("storage", {"dataRoot": str(base / "data")}, revision=eff.revisions["storage"])
provider.write("preview", {"cacheDir": str(base / "data" / "preview")}, revision=eff.revisions["preview"])
provider.write("api", {"webRoot": str(root / "modules/web/app/dist")}, revision=eff.revisions["api"])
PY

export PYTHONPATH="$ROOT/modules/api/src:$ROOT/modules/config/src:$ROOT/modules/storage/src:$ROOT/modules/uploads/src:$ROOT/modules/preview/src:$ROOT/modules/media-metadata/src:$ROOT/modules/archive-zip/src:$ROOT/modules/pipeline/src:$ROOT/modules/core-time/python:$ROOT/modules/worker/src"
MOYU_CONFIG_DIR="$TMP/config" \
MOYU_API_LISTEN="127.0.0.1:$PORT" \
MOYU_BOOTSTRAP_TOKEN_FILE="$TMP/secrets/bootstrap_token" \
MOYU_SESSION_STATE_FILE="$TMP/config/secrets/session-state.json" \
MOYU_SESSION_SECRET_FILE="$TMP/config/secrets/session.secret" \
  python3 -m moyu_api >"$API_LOG" 2>&1 &
API_PID=$!
MOYU_CONFIG_DIR="$TMP/config" python3 -m moyu_worker >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!

for _ in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/v1/health" || true)"
  [ "$code" = "200" ] && break
  sleep 1
done
[ "${code:-}" = "200" ] || { echo "API 未启动"; exit 1; }

cd "$ROOT/modules/web/app"
MOYU_E2E_BASE_URL="http://127.0.0.1:$PORT" \
MOYU_E2E_BOOTSTRAP=e2e-boot-token \
MOYU_E2E_PASSWORD=e2e-secret-pass \
  npx playwright test --config playwright.fullstack.config.ts
