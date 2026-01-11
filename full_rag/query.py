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


def generate_with_llm(query, contexts):
    context_text = "\n".join(contexts)
    prompt = (
        "You are a helpful assistant. Use only the context to answer. "
        "If the answer is not in the context, say you do not know. "
        "If the question is in Japanese, answer in Japanese.\n\n"
        f"Context:\n{context_text}\n\nQuestion: {query}\nAnswer:"
    )
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python query.py 'your question'")
        sys.exit(1)

    cfg = default_config()
    if not cfg.index_path.exists() or not cfg.metadata_path.exists():
        print("Index not found. Run: python ingest.py")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    metadata = load_metadata(cfg.metadata_path)

    index = faiss.read_index(str(cfg.index_path))
    model = SentenceTransformer(cfg.embed_model_name)
    query_vec = model.encode([query]).astype("float32")
    faiss.normalize_L2(query_vec)

    scores, ids = index.search(query_vec, cfg.top_k)
    contexts = [metadata[i]["text"] for i in ids[0] if i != -1]

    if os.environ.get("LLAMA_MODEL_PATH"):
        answer = generate_with_llm(query, contexts)
    else:
        answer = "\n".join(contexts)
        answer = "Top contexts (no local LLM configured):\n" + answer

    print(answer)


if __name__ == "__main__":
    main()
