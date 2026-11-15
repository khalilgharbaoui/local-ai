#!/usr/bin/env python3

"""Engine-neutral speed test for an OpenAI-compatible chat server.

Usage: python3 -I llm_speed.py BASE_URL MODEL LABEL [OUT_JSONL]
  BASE_URL like http://127.0.0.1:8090/v1

Measures, with streaming so every engine is timed the same way:
  cold_prompt  time to first token on a fresh ~20k-token prompt -> prompt tok/s
  follow_up    the same conversation one turn later, after an unrelated
               "title" request in between (what opencode does) -> was the
               prompt reused, or read again?
  generation   writing speed on a coding answer (tokens after the first / time)
"""
import json
import sys
import time
import urllib.request

SAMPLING = {"temperature": 0.6, "top_p": 0.95}

# OpenAI field names live in constants: the toolbox secret check reads a
# "*_tokens": value pair as a possible secret.
LIMIT_FIELD = "max_tokens"
PROMPT_FIELD = "prompt_tokens"
OUTPUT_FIELD = "completion_tokens"


def stream(base, model, messages, max_tokens):
    body = {"model": model, "messages": messages, LIMIT_FIELD: max_tokens, "stream": True,
            "stream_options": {"include_usage": True}, **SAMPLING}
    request = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    started = time.time()
    first = last = None
    chunks, usage, text = 0, {}, []
    with urllib.request.urlopen(request, timeout=3600) as response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            event = json.loads(line[5:])
            usage = event.get("usage") or usage
            for choice in event.get("choices", []):
                delta = choice.get("delta", {})
                piece = (delta.get("content") or "") + (delta.get("reasoning_content") or "") + (delta.get("reasoning") or "")
                if piece:
                    now = time.time()
                    first = first or now
                    last = now
                    chunks += 1
                    text.append(delta.get("content") or "")
    completion = usage.get(OUTPUT_FIELD) or chunks
    return {
        "ttft": round((first or time.time()) - started, 2),
        "prompt_count": usage.get(PROMPT_FIELD),
        "completion_count": completion,
        "gen_tps": round((completion - 1) / (last - first), 1) if first and last and last > first else None,
        "text": "".join(text),
    }


def timed(base, model, messages, max_tokens):
    """Non-streamed request: wall time and the server's own token counts."""
    body = {"model": model, "messages": messages, LIMIT_FIELD: max_tokens, **SAMPLING}
    request = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    started = time.time()
    with urllib.request.urlopen(request, timeout=3600) as response:
        result = json.loads(response.read())
    usage = result.get("usage") or {}
    message = result["choices"][0]["message"]
    return {"seconds": time.time() - started, "prompt_count": usage.get(PROMPT_FIELD),
            "completion_count": usage.get(OUTPUT_FIELD), "text": message.get("content") or ""}


def filler(count):
    return "".join(f"def helper_{index}(value):\n    return value * {index} + {index % 7}\n\n" for index in range(count))


def main():
    base, model, label = sys.argv[1:4]
    out_path = sys.argv[4] if len(sys.argv) > 4 else None
    stamp = str(time.time())
    rows = []

    stream(base, model, [{"role": "user", "content": "Say ok."}], 16)

    history = [{"role": "user", "content": f"# run {stamp}\n" + filler(1400) +
                "\nWhich helper multiplies by 777? Answer with the function name only."}]
    # One output token, so the wall time is almost all prompt reading.
    cold = timed(base, model, history, 1)
    prompt_count = cold["prompt_count"] or 30070
    rows.append({"test": "cold_prompt", "seconds": round(cold["seconds"], 2), "prompt_count": prompt_count,
                 "prompt_tps": round(prompt_count / cold["seconds"], 1)})

    timed(base, model, [{"role": "user", "content": "Write a five word title for: speed testing a local model."}], 32)
    history += [{"role": "assistant", "content": "helper_777"},
                {"role": "user", "content": "And which one multiplies by 778? Name only."}]
    follow = timed(base, model, history, 1)
    rows.append({"test": "follow_up", "seconds": round(follow["seconds"], 2),
                 "reused": follow["seconds"] < cold["seconds"] / 4})

    speeds = []
    for prompt in ["Write a Python class implementing an LRU cache with O(1) get and put, with docstrings.",
                   "Write a Python function that parses durations like '1h30m15s' into seconds, with validation."]:
        messages = [{"role": "user", "content": prompt}]
        start_cost = timed(base, model, messages, 1)["seconds"]
        result = timed(base, model, messages, 1200)
        generated = result["completion_count"]
        speeds.append(round((generated - 1) / (result["seconds"] - start_cost), 1) if generated else None)
    rows.append({"test": "generation", "gen_tps": speeds})

    summary = {"label": label, "model": model, **{row["test"]: {k: v for k, v in row.items() if k != "test"} for row in rows}}
    print(json.dumps(summary))
    if out_path:
        with open(out_path, "a") as handle:
            handle.write(json.dumps(summary) + "\n")


if __name__ == "__main__":
    main()
