#!/usr/bin/env python3
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import default_config
from utils import chunk_text, load_texts, save_metadata


def main():
    cfg = default_config()
    cfg.results_dir.mkdir(parents=True, exist_ok=True)
    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    docs = load_texts([cfg.data_dir, cfg.results_dir])
    chunks = []
    metadata = []
    for filename, text in docs:
        for idx, chunk in enumerate(chunk_text(text, cfg.chunk_size, cfg.chunk_overlap)):
            chunks.append(chunk)
            metadata.append({"source": filename, "chunk": idx, "text": chunk})

    model = SentenceTransformer(cfg.embed_model_name)
    embeddings = model.encode(chunks, show_progress_bar=True)
    embeddings = np.asarray(embeddings, dtype="float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    faiss.write_index(index, str(cfg.index_path))
    save_metadata(cfg.metadata_path, metadata)
    print(f"Indexed {len(chunks)} chunks to {cfg.index_path}")


if __name__ == "__main__":
    main()
