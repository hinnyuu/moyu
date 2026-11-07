#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
IMAGE="${MOYU_SMOKE_IMAGE:-moyu:smoke}"
PUBLIC_PORT="${MOYU_SMOKE_PUBLIC_PORT:-18080}"
API_PORT="${MOYU_SMOKE_API_PORT:-18081}"
PREVIEW_PORT="${MOYU_SMOKE_PREVIEW_PORT:-18082}"
TUSD_PORT="${MOYU_SMOKE_TUSD_PORT:-18083}"
GATEWAY_PORT="${MOYU_SMOKE_GATEWAY_PORT:-18443}"
ADMIN_PORT="${MOYU_SMOKE_ADMIN_PORT:-19443}"
POD="moyu-smoke-$$"
TMP="$(mktemp -d)"

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "--- podman ps ---"
    podman ps -a || true
    echo "--- api logs ---"
    podman logs "${POD}-api" 2>&1 | tail -40 || true
    echo "--- preview logs ---"
    podman logs "${POD}-preview" 2>&1 | tail -40 || true
    echo "--- tusd logs ---"
    podman logs "${POD}-tusd" 2>&1 | tail -40 || true
    echo "--- worker logs ---"
    podman logs "${POD}-worker" 2>&1 | tail -40 || true
    echo "--- gateway logs ---"
    podman logs "${POD}-gateway" 2>&1 | tail -40 || true
  fi
  podman pod rm -f "$POD" >/dev/null 2>&1 || true
  rm -rf "$TMP"
  exit "$status"
}
trap cleanup EXIT

mkdir -p "$TMP/config/secrets" "$TMP/data" "$TMP/secrets" "$TMP/certs"
chmod -R 0777 "$TMP/config" "$TMP/data"
echo smoke-boot > "$TMP/secrets/bootstrap_token"
echo smoke-admin-token > "$TMP/config/secrets/gateway_reload_token"
chmod -R a+rX "$TMP/secrets"
chmod 0644 "$TMP/config/secrets/gateway_reload_token"

PYTHONPATH="$ROOT/modules/config/src" python3 "$ROOT/modules/deploy/scripts/make_smoke_config.py" \
  "$TMP/config" \
  --data-root /data \
  --cache-dir /data/preview \
  --web-root /app/web \
  --upstream "http://127.0.0.1:${API_PORT}" \
  --gateway-port "${GATEWAY_PORT}" \
  --cert-dir /certs \
  --admin-port "${ADMIN_PORT}" \
  --preview-url "http://127.0.0.1:${PREVIEW_PORT}"

openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "$TMP/certs/tls.key" -out "$TMP/certs/tls.crt" -days 1 \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
chmod 0644 "$TMP/certs/tls.crt" "$TMP/certs/tls.key"
chmod -R 0777 "$TMP/config" "$TMP/data"

podman pod create --name "$POD" -p "${PUBLIC_PORT}:${GATEWAY_PORT}"

podman run -d --pod "$POD" --name "${POD}-api" \
  -e MOYU_CONFIG_DIR=/config \
  -e MOYU_API_LISTEN="0.0.0.0:${API_PORT}" \
  -e MOYU_BOOTSTRAP_TOKEN_FILE=/run/secrets/bootstrap_token \
  -e MOYU_SESSION_STATE_FILE=/config/secrets/session-state.json \
  -e MOYU_SESSION_SECRET_FILE=/config/secrets/session.secret \
  -e MOYU_TUSD_HOOK_TOKEN=smoke-hook-token \
  -v "$TMP/config:/config" \
  -v "$TMP/data:/data" \
  -v "$TMP/secrets:/run/secrets:ro" \
  "$IMAGE" api

podman run -d --pod "$POD" --name "${POD}-preview" \
  -e MOYU_CONFIG_DIR=/config \
  -e MOYU_PREVIEW_LISTEN="0.0.0.0:${PREVIEW_PORT}" \
  -v "$TMP/config:/config:ro" \
  -v "$TMP/data:/data" \
  "$IMAGE" preview

podman run -d --pod "$POD" --name "${POD}-tusd" \
  -e MOYU_TUSD_LISTEN="0.0.0.0:${TUSD_PORT}" \
  -e MOYU_TUSD_UPLOAD_DIR=/data/tusd \
  -e MOYU_TUSD_BASE_PATH=/files/ \
  -e MOYU_TUSD_HOOK_URL="http://127.0.0.1:${API_PORT}/api/v1/internal/tusd/hook" \
  -e MOYU_TUSD_HOOK_TOKEN=smoke-hook-token \
  -v "$TMP/data:/data" \
  "$IMAGE" tusd

podman run -d --pod "$POD" --name "${POD}-worker" \
  -e MOYU_CONFIG_DIR=/config \
  -v "$TMP/config:/config:ro" \
  -v "$TMP/data:/data" \
  "$IMAGE" worker

podman run -d --pod "$POD" --name "${POD}-gateway" \
  -e MOYU_GATEWAY_CONFIG=/config/modules/gateway.yaml \
  -v "$TMP/config:/config:ro" \
  -v "$TMP/certs:/certs:ro" \
  -v "$TMP/secrets:/run/secrets:ro" \
  "$IMAGE" gateway

echo "waiting for gateway TLS health..."
ok=0
for _ in $(seq 1 60); do
  code="$(curl -k -s -o /dev/null -w '%{http_code}' "https://127.0.0.1:${PUBLIC_PORT}/api/v1/health" || true)"
  if [ "$code" = "200" ]; then ok=1; break; fi
  sleep 1
done
if [ "$ok" -ne 1 ]; then
  echo "gateway health failed" >&2
  exit 1
fi

status="$(curl -k -s -c "$TMP/cookies" -o "$TMP/login.json" -w '%{http_code}' \
  -X POST "https://127.0.0.1:${PUBLIC_PORT}/api/v1/auth/session" \
  -H 'Content-Type: application/json' \
  -d '{"bootstrap_token":"smoke-boot","password":"smoke-pass-123"}')"
if [ "$status" != "204" ]; then
  echo "login failed: $status" >&2
  cat "$TMP/login.json" >&2 || true
  exit 1
fi

session="$(curl -k -s -b "$TMP/cookies" "https://127.0.0.1:${PUBLIC_PORT}/api/v1/auth/session")"
echo "$session" | grep -q '"username":"admin"'
echo "$session" | grep -q '"csrf"'

for name in worker preview tusd; do
  if ! podman ps --format '{{.Names}}' | grep -q "${POD}-${name}"; then
    echo "${name} container is not running" >&2
    exit 1
  fi
done

echo "PASS: image roles, pod networking, TLS gateway, preview/tusd containers, config/data/secrets mounts, session login"
