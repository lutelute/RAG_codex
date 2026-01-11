#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import default_config
from utils import load_metadata


def retrieve_contexts(query, cfg):
    metadata = load_metadata(cfg.metadata_path)
    index = faiss.read_index(str(cfg.index_path))
    model = SentenceTransformer(cfg.embed_model_name)
    query_vec = model.encode([query]).astype("float32")
    faiss.normalize_L2(query_vec)
    _, ids = index.search(query_vec, cfg.top_k)
    return [metadata[i]["text"] for i in ids[0] if i != -1]


def call_llm(prompt):
    script = Path(__file__).parent / "llm_generate.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        input=prompt,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return "LLM failed: " + (result.stderr.strip() or "unknown error")
    return result.stdout.strip()


def run_python(code):
    result = subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        capture_output=True,
        timeout=10,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if result.returncode != 0:
        return f"error: {stderr or 'unknown error'}"
    return stdout or "(no output)"


def parse_tool_response(text):
    lines = text.strip().splitlines()
    if not lines:
        return ("FINAL", "")
    head = lines[0].strip()
    if head == "PYTHON":
        try:
            end_idx = lines.index("END")
        except ValueError:
            return ("FINAL", text)
        code = "\n".join(lines[1:end_idx]).strip()
        return ("PYTHON", code)
    if head == "FINAL":
        return ("FINAL", "\n".join(lines[1:]).strip())
    return ("FINAL", text)


def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py 'your question'")
        sys.exit(1)

    if not os.environ.get("LLAMA_MODEL_PATH"):
        print("LLAMA_MODEL_PATH is not set. Agent mode requires a local LLM.")
        sys.exit(1)

    cfg = default_config()
    if not cfg.index_path.exists() or not cfg.metadata_path.exists():
        print("Index not found. Run: python ingest.py")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    contexts = retrieve_contexts(query, cfg)
    context_text = "\n".join(contexts)

    system_prompt = (
        "You are a local RAG agent. Use the provided context to answer. "
        "If you need to compute something, you may ask to run Python. "
        "If the question is in Japanese, answer in Japanese.\n\n"
        "Respond in one of these exact formats:\n"
        "PYTHON\n<code>\nEND\n"
        "or\n"
        "FINAL\n<answer>\n"
        "Do not add any extra text outside the format."
    )

    prompt = (
        system_prompt
        + "\n\nContext:\n"
        + context_text
        + "\n\nQuestion: "
        + query
        + "\nAnswer:"
    )
    response = call_llm(prompt)
    mode, payload = parse_tool_response(response)

    if mode == "PYTHON":
        tool_output = run_python(payload)
        followup = (
            system_prompt
            + "\n\nContext:\n"
            + context_text
            + "\n\nQuestion: "
            + query
            + "\n\nPython output:\n"
            + tool_output
            + "\n\nAnswer:"
        )
        response = call_llm(followup)
        mode, payload = parse_tool_response(response)

    if mode != "FINAL":
        payload = response
    print(payload)


if __name__ == "__main__":
    main()
