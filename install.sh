#!/usr/bin/env bash
# Install local-ai-server on an Apple Silicon Mac. Safe to run again: each step skips
# what is already in place.
#   ./install.sh               build llama.cpp, link the scripts, write models.ini, start the service
#   ./install.sh --no-service  everything except the launch agent
set -euo pipefail
repo=$(cd "$(dirname "$0")" && pwd)
label="com.$(id -un).local-ai-server"
agent="$HOME/Library/LaunchAgents/$label.plist"
ini="$HOME/.config/local-ai/models.ini"
model_repo="DavidAU/Qwen3.8-27B-TURBO-Fable-Cold-Fusion-735-882-Heretic-Uncensored-NEO-CODER-MAX-MTP-GGUF"
model_file="Qwen3.8-27B-TurboFCFusion-735-882-Here-Uncen-NEO-CODER-MAX-MTP-IQ4_XS.gguf"
step() { printf '\n== %s\n' "$*"; }

[ "$(uname -sm)" = "Darwin arm64" ] || { echo "install.sh: needs an Apple Silicon Mac" >&2; exit 1; }

step "llama.cpp"
"$repo/scripts/build-llama.sh"

step "scripts in ~/.local/bin"
mkdir -p "$HOME/.local/bin"
for script in local-ai-server local-ai-logs; do
  ln -sfn "$repo/bin/$script" "$HOME/.local/bin/$script"
  echo "linked $script"
done

step "models.ini"
if [ -f "$ini" ]; then
  echo "keeping $ini"
else
  command -v hf > /dev/null || { echo "install.sh: the Hugging Face CLI is needed for the download (brew install hf)" >&2; exit 1; }
  path=$(hf download "$model_repo" "$model_file" | tail -1 | sed 's/^path=//')
  mkdir -p "$(dirname "$ini")"
  sed "s|^model = .*|model = $path|" "$repo/config/models.ini.example" > "$ini"
  echo "wrote $ini"
fi

if [ "${1:-}" = "--no-service" ]; then
  step "launch agent skipped (--no-service)"
  exit 0
fi

step "launch agent $label"
mkdir -p "$(dirname "$agent")"
sed "s|__LABEL__|$label|g" "$repo/launchd/local-ai-server.plist" > "$agent.new"
if cmp -s "$agent.new" "$agent"; then
  rm "$agent.new"
  echo "unchanged, still running"
else
  mv "$agent.new" "$agent"
  launchctl bootout "gui/$(id -u)/$label" 2> /dev/null && sleep 2 || true
  launchctl bootstrap "gui/$(id -u)" "$agent"
  echo "started; read its logs with local-ai-logs"
fi

step "opencode"
echo "add the providers in $repo/opencode/provider.json to ~/.config/opencode/opencode.json (see README)"
