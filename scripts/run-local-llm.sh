#!/usr/bin/env bash
# Start llama-server for local dev. Prefers tools/llama-runtime (GPU backends); falls back to PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RUNTIME="$ROOT/tools/llama-runtime"
MODEL="${LOCAL_LLM_GGUF:-models/gemma-2-2b-it-Q4_K_M.gguf}"
HOST="${LOCAL_LLM_BIND:-127.0.0.1}"
PORT="${LOCAL_LLM_PORT:-8765}"
ALIAS="${LOCAL_LLM_MODEL:-gemma-2-2b-it}"

if [[ -x "$RUNTIME/llama-server" ]]; then
  SERVER="$RUNTIME/llama-server"
  export LD_LIBRARY_PATH="$RUNTIME${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    export DYLD_LIBRARY_PATH="$RUNTIME${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
  fi
elif command -v llama-server >/dev/null 2>&1; then
  SERVER="$(command -v llama-server)"
else
  echo "llama-server not found. Run: mise run init" >&2
  exit 1
fi

exec "$SERVER" -m "$MODEL" --host "$HOST" --port "$PORT" -a "$ALIAS" -ngl auto "$@"
