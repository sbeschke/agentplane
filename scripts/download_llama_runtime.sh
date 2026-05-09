#!/usr/bin/env bash
# Download a GPU-capable llama.cpp build from official releases (not the CPU-only default).
# Linux x86_64: ubuntu-vulkan (NVIDIA/AMD via Vulkan). macOS arm64: Metal. See docs/decisions.md.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BUILD="${LLAMA_CPP_BUILD:-9090}"
DEST="$ROOT/tools/llama-runtime"

if [[ -x "$DEST/llama-server" ]]; then
  echo "llama.cpp runtime already present: $DEST"
  exit 0
fi

OS=$(uname -s)
ARCH=$(uname -m)
case "$ARCH" in
x86_64 | amd64) A=x86_64 ;;
arm64 | aarch64) A=arm64 ;;
*)
  echo "Unsupported architecture: $ARCH" >&2
  exit 1
  ;;
esac

if [[ "$OS" == "Linux" && "$A" == "x86_64" ]]; then
  ASSET="llama-b${BUILD}-bin-ubuntu-vulkan-x64.tar.gz"
elif [[ "$OS" == "Linux" && "$A" == "arm64" ]]; then
  ASSET="llama-b${BUILD}-bin-ubuntu-arm64.tar.gz"
elif [[ "$OS" == "Darwin" && "$A" == "arm64" ]]; then
  ASSET="llama-b${BUILD}-bin-macos-arm64.tar.gz"
elif [[ "$OS" == "Darwin" && "$A" == "x86_64" ]]; then
  ASSET="llama-b${BUILD}-bin-macos-x64.tar.gz"
else
  echo "Unsupported platform: $OS $ARCH" >&2
  exit 1
fi

URL="https://github.com/ggml-org/llama.cpp/releases/download/b${BUILD}/${ASSET}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Downloading llama.cpp runtime ${ASSET} ..."
curl -fL --retry 3 --retry-delay 2 -o "$TMP/archive.tar.gz" "$URL"
tar -xzf "$TMP/archive.tar.gz" -C "$TMP"

INNER="llama-b${BUILD}"
if [[ ! -d "$TMP/$INNER" ]]; then
  echo "Unexpected archive layout (missing $INNER). Contents:" >&2
  ls -la "$TMP" >&2
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
mv "$TMP/$INNER" "$DEST"
echo "Installed llama-server (GPU-capable build where available): $DEST/llama-server"
