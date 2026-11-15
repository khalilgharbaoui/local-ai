#!/usr/bin/env bash
# Build llama.cpp's llama-server with Metal into ~/.local/opt/llama-upstream-<tag>, the
# path local-ai-server uses by default. Skips the build when that binary already exists.
#   scripts/build-llama.sh [TAG]     default b12383 (llama.cpp 1.0.0)
set -euo pipefail
tag="${1:-b12383}"
src="$HOME/.local/src/llama.cpp-$tag"
opt="$HOME/.local/opt/llama-upstream-$tag"

if [ -x "$opt/llama-server" ]; then
  echo "already built: $opt/llama-server"
  exit 0
fi
for tool in git cmake xcrun; do
  command -v "$tool" > /dev/null || { echo "build-llama.sh: $tool is missing (Xcode and brew install cmake)" >&2; exit 1; }
done

rm -rf "$src"
mkdir -p "$(dirname "$src")"
git clone -q --depth 1 --branch "$tag" https://github.com/ggml-org/llama.cpp "$src"
cmake -S "$src" -B "$src/build" -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF
cmake --build "$src/build" -j --target llama-server
mkdir -p "$opt"
cp -R "$src/build/bin/." "$opt/"
"$opt/llama-server" --version 2>&1 | head -1
