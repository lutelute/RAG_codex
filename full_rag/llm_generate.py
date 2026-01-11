#!/usr/bin/env python3
import os
import sys


def main():
    model_path = os.environ.get("LLAMA_MODEL_PATH")
    if not model_path:
        print("LLAMA_MODEL_PATH is not set", file=sys.stderr)
        sys.exit(1)

    try:
        from llama_cpp import Llama
    except Exception as exc:
        print(f"Failed to import llama_cpp: {exc}", file=sys.stderr)
        sys.exit(1)

    prompt = sys.stdin.read()
    if not prompt.strip():
        print("Prompt is empty", file=sys.stderr)
        sys.exit(1)

    threads = os.cpu_count() or 4
    llm = Llama(
        model_path=model_path,
        n_ctx=1024,
        n_threads=min(4, threads),
        n_gpu_layers=0,
        use_mmap=False,
        verbose=False,
    )
    output = llm(prompt, max_tokens=256)
    sys.stdout.write(output["choices"][0]["text"].strip())


if __name__ == "__main__":
    main()
