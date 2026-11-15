# local-ai

A local coding model for [opencode](https://opencode.ai) on an Apple Silicon Mac. A llama.cpp
server starts at login, loads the model when a request arrives, unloads it after 30 idle minutes,
and keeps the Mac awake only while a model is loaded. Ollama serves two more models next to it.

Measured on a MacBook Pro M5 Pro with 48 GB. [RESULTS.md](RESULTS.md) lists what was tried and
what each setting did.

| Model | Engine | Prompt reading | Writing | Coding eval |
|---|---|---|---|---|
| Qwen3.8 27B Fable Coder, IQ4_XS + MTP | llama.cpp 1.0.0 | 297 tok/s | 24.5 tok/s | 7/7 |
| Qwen3.8 27B Fable Coder, NVFP4 | Ollama (MLX) | 338 tok/s | 22-25 tok/s | 7/7 |
| Qwen3.8 27B stock, NVFP4 + DFlash2 | Ollama (MLX) | 416 tok/s | 30-35 tok/s | 5/7 (measured on llama.cpp) |

## Requirements

- An Apple Silicon Mac with 48 GB of memory or more. The model needs about 26 GB.
- Xcode, and Homebrew with `cmake` and `hf` (`brew install cmake hf`).
- About 20 GB of free disk for the model, plus 21 GB per Ollama model.

## Install

```bash
git clone <this repo> ~/code/local-ai
cd ~/code/local-ai
./install.sh
```

`install.sh` builds llama.cpp 1.0.0 with Metal, links `local-ai-server` and `local-ai-logs`
into `~/.local/bin`, downloads the model and writes `~/.config/local-ai/models.ini`, then starts
the launch agent `com.<you>.local-ai-server`. Run it again after a change; every step skips what
is already done. `./install.sh --no-service` skips the launch agent, so you start
`local-ai-server` by hand.

Check that it answers. The first request loads the model, which takes about 20 seconds:

```bash
curl -s http://127.0.0.1:8090/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-27b-fable-coder-mtp","messages":[{"role":"user","content":"Say ok."}]}'
```

## Use it in opencode

Add the two providers from [opencode/provider.json](opencode/provider.json) to the `provider`
section of `~/.config/opencode/opencode.json`, then restart opencode. The models show up under
"Local (llama.cpp)" and "Local (Ollama)" in the model picker.

Use one local model at a time. Fable on llama.cpp stays loaded for 30 minutes after its last
request and an Ollama model for 5, and two loaded at once can run the GPU out of memory.

## Logs

```bash
local-ai-logs        # last 200 lines
local-ai-logs 1000   # last 1000 lines
local-ai-logs -e     # only warnings, errors and start and keep-awake events
local-ai-logs -f     # follow live
```

Logs live in `~/Library/Logs/local-ai-server/`. They rotate at 10 MB with 5 old files kept, so
they never use more than about 60 MB.

## Settings

Set these in the launch agent's `EnvironmentVariables`, or before `local-ai-server` when you run
it by hand.

| Variable | Default | Meaning |
|---|---|---|
| `LOCAL_AI_PORT` | `8090` | Port of the OpenAI-compatible API |
| `LOCAL_AI_IDLE_SECONDS` | `1800` | Unload the model after this long without requests; `0` keeps it loaded |
| `LOCAL_AI_CACHE_GB` | `8` | Memory for cached prompts, so follow-up turns skip rereading |
| `LOCAL_AI_LLAMA` | upstream build | Path to another `llama-server` |

Model settings (the thinking level, the MTP draft) are in `~/.config/local-ai/models.ini`.

## Ollama models

Ollama runs its own service. These settings measured best; they go into Homebrew's launch agent:

```bash
plist=~/Library/LaunchAgents/homebrew.mxcl.ollama.plist   # or sh.brew.ollama.plist
plutil -replace EnvironmentVariables.OLLAMA_CONTEXT_LENGTH -string 131072 "$plist"
plutil -replace EnvironmentVariables.OLLAMA_KEEP_ALIVE -string 5m "$plist"
plutil -replace EnvironmentVariables.OLLAMA_FLASH_ATTENTION -string 1 "$plist"
plutil -replace EnvironmentVariables.OLLAMA_KV_CACHE_TYPE -string q8_0 "$plist"
brew services restart ollama
```

The stock model: `ollama pull qwen3.8:27b-dflash2-nvfp4`. Fable in Ollama:
`scripts/ollama-import-fable.sh`, which downloads the full weights (51 GB), converts them to
NVFP4 and deletes the download.

## On battery

macOS Low Power Mode makes a 27B model about three times slower. `local-ai-server` warns about
it at start. To keep full speed on battery: `sudo pmset -b powermode 0`.

## Benchmarks

```bash
python3 -I bench/llm-speed.py http://127.0.0.1:8090/v1 qwen3.8-27b-fable-coder-mtp my-label
python3 -I bench/eval.py results/ qwen3.8-27b-fable-coder-mtp
```

`llm-speed.py` measures a cold 30k-token prompt, a follow-up turn after a title request (as
opencode sends one) and writing speed, the same way for any OpenAI-compatible server.
`eval.py` runs 7 coding tasks with tests, a tool edit, a long-context lookup and two refusal
checks. `EVAL_BASE` points it at another server and `EVAL_EFFORT` sets the thinking level.

## Uninstall

```bash
launchctl bootout gui/$(id -u)/com.$(id -un).local-ai-server
rm ~/Library/LaunchAgents/com.$(id -un).local-ai-server.plist ~/.local/bin/local-ai-server ~/.local/bin/local-ai-logs
```

## Credits

- [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT) and [Ollama](https://ollama.com)
- Fable Coder: [DavidAU](https://huggingface.co/DavidAU) and Nightmedia, built on
  [Qwen3.8 27B](https://huggingface.co/Qwen/Qwen3.8-27B); both Apache 2.0

The scripts in this repo are MIT licensed.
