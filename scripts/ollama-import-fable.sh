#!/usr/bin/env bash
# Import Fable into Ollama as an MLX NVFP4 model (about 21 GB). Downloads the full weights
# (about 51 GB of free disk needed), lets Ollama convert them, then deletes the download.
#   scripts/ollama-import-fable.sh [NAME]     default fable-coder:27b-nvfp4
set -euo pipefail
name="${1:-fable-coder:27b-nvfp4}"
weights_repo="DavidAU/Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NM-DAU"

snapshot=$(hf download "$weights_repo" | tail -1 | sed 's/^path=//')
modelfile=$(mktemp)
printf 'FROM %s\n' "$snapshot" > "$modelfile"
ollama create "$name" --quantize nvfp4 -f "$modelfile"
rm -f "$modelfile"
hf cache rm "model/$weights_repo" -y
ollama list | grep -F "$name"
