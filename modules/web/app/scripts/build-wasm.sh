#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
if ! command -v wasm-pack >/dev/null 2>&1; then
  echo "需要 wasm-pack：https://rustwasm.github.io/wasm-pack/installer/" >&2
  exit 1
fi
wasm-pack build "$ROOT/modules/wasm-client/rust" \
  --target web \
  --out-dir "$ROOT/modules/web/app/public/wasm"
echo "wasm 输出：modules/web/app/public/wasm"
