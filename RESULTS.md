# Results

MacBook Pro M5 Pro, 48 GB, on the charger, November 2026. Speed from `bench/llm-speed.py`:
a cold 30k-token prompt, a follow-up turn after a title request, and two coding answers.
Quality from `bench/eval.py`: 7 coding tasks with tests.

## Kept

| Change | Effect |
|---|---|
| Upstream llama.cpp 1.0.0 (b12383) instead of the PrismML fork (b12128) | Writing 21-23 to 24.5-24.9 tok/s; MTP accepts 3.3 tokens per step instead of 2.5 |
| `reasoning-effort = medium` instead of the template default `xhigh` | 13% less time and tokens, still 7/7 |
| Prompt cache (`--cache-ram`, `--ctx-checkpoints`) | Follow-up turns in 1.5-3 s instead of rereading 30k tokens (about 100 s) |
| Ollama with flash attention and q8_0 KV cache | Stock Qwen: 354 to 400-416 tok/s prompt reading |
| `sudo pmset -b powermode 0` | About 3x faster on battery than Low Power Mode |

## Thinking level (Fable, 7 coding tasks)

| Level | Passed | Tokens | Time |
|---|---|---|---|
| `xhigh` (template default) | 7/7 | 8,695 | 363 s |
| `medium` | 7/7 | 7,535 | 317 s |
| `low` | 6/7 | 5,785 | 253 s |

## Rejected

| Tried | Result |
|---|---|
| q4_0 KV cache | 6 GB less memory, but prompt reading 15% slower (253 tok/s) |
| q8_0 KV cache | Prompt reading 17% slower (247 tok/s), 4 GB less memory |
| DFlash2 draft model on Fable | 3-4% of guesses accepted, writing fell to 9 tok/s; the draft only fits stock Qwen |
| `GGML_METAL_TENSOR_ENABLE=1` | Prompt reading 11% slower, follow-ups 18 s |
| `LLAMA_MTP_CHAIN=1` (fork) | Crashes: `GGML_ASSERT(ubatch.token && ubatch.embd)`; with a guard it crashes later in `llama-context.cpp` |
| Q4_K_S instead of IQ4_XS | No measurable difference |
| MTPLX 2.12.3 | Its memory guard refused the 30k prompt on 48 GB (HTTP 507) |
| Homebrew llama.cpp 0.9.0 | Older than both builds above |

## Memory

The bottleneck on a 48 GB Mac is memory, not compute. With many apps open the Mac swaps
before a model loads, and two local models loaded at once run the GPU out of memory
(`kIOGPUCommandBufferCallbackErrorOutOfMemory`). Fable on llama.cpp takes about 26 GB with a
128k context, an Ollama model about 21 GB.
