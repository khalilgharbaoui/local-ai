#!/usr/bin/env bash
# Publish the local Fable import (scripts/ollama-import-fable.sh) to ollama.com as
# USERNAME/fable-coder:27b-nvfp4, with the Apache 2.0 license and credits attached.
# Sign in first with `ollama signin`. The copy shares the original's files, so it takes no
# extra disk. NO_PUSH=1 builds the copy without pushing it.
#   scripts/ollama-push-fable.sh USERNAME
set -euo pipefail
user="${1:?usage: ollama-push-fable.sh USERNAME}"
source_model="fable-coder:27b-nvfp4"
target="$user/$source_model"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o "$work/apache-2.0.txt"
{
  printf 'FROM %s\n' "$source_model"
  printf 'LICENSE """'
  cat << 'NOTICE'
Qwen3.8 27B TURBO Fable Cold Fusion 735-882 Heretic Uncensored, converted to NVFP4 for
Ollama's MLX runner with `ollama create --quantize nvfp4`. Nothing else was changed.

Model by DavidAU and Nightmedia:
https://huggingface.co/DavidAU/Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NM-DAU
Built on Qwen3.8 27B by the Qwen team: https://huggingface.co/Qwen/Qwen3.8-27B
Both are licensed under the Apache License 2.0, reproduced below.

NOTICE
  cat "$work/apache-2.0.txt"
  printf '"""\n'
} > "$work/Modelfile"

ollama create "$target" -f "$work/Modelfile"
if [ "${NO_PUSH:-0}" = 1 ]; then
  echo "built $target locally, not pushed (NO_PUSH=1)"
  exit 0
fi
ollama push "$target"
