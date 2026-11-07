#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
if ! command -v wasm-bindgen >/dev/null 2>&1; then
  echo "需要 wasm-bindgen CLI：" >&2
  echo "  cargo install wasm-bindgen-cli --version 0.2.130 --locked" >&2
  exit 1
fi
cd "$ROOT"
cargo build -p moyu-wasm-client --target wasm32-unknown-unknown --release
mkdir -p modules/web/app/public/wasm
wasm-bindgen \
  --target web \
  --out-dir modules/web/app/public/wasm \
  target/wasm32-unknown-unknown/release/moyu_wasm_client.wasm
echo "wasm 输出：modules/web/app/public/wasm"
