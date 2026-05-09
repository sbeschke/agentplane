#!/usr/bin/env bash
# Download the default local GGUF used by process-compose (CPU-friendly Gemma 2 2B IT).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="${MODEL_DIR:-$ROOT/models}"
MODEL_FILE="${MODEL_FILE:-gemma-2-2b-it-Q4_K_M.gguf}"
# bartowski community quant; pin file for reproducible init
URL="${LOCAL_LLM_DOWNLOAD_URL:-https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/${MODEL_FILE}}"
DEST="$MODEL_DIR/$MODEL_FILE"

mkdir -p "$MODEL_DIR"
if [[ -f "$DEST" ]] && [[ -s "$DEST" ]]; then
  echo "Local LLM weights already present: $DEST"
  exit 0
fi

echo "Downloading local LLM weights to $DEST ..."
if command -v curl >/dev/null 2>&1; then
  curl -fL --retry 3 --retry-delay 2 -o "$DEST.partial" "$URL"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$DEST.partial" "$URL"
else
  echo "Need curl or wget to download weights." >&2
  exit 1
fi
mv "$DEST.partial" "$DEST"
echo "Done: $DEST"
