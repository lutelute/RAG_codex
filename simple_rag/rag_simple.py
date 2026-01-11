#!/usr/bin/env python3
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path


def tokenize(text):
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def load_docs(data_dir):
    docs = []
    for path in sorted(Path(data_dir).glob("*.txt")):
        docs.append((path.name, path.read_text(encoding="utf-8")))
    return docs


def build_tfidf(docs):
    doc_tokens = []
    df = Counter()
    for _, text in docs:
        tokens = tokenize(text)
        doc_tokens.append(tokens)
        df.update(set(tokens))
    n_docs = len(docs)
    idf = {term: math.log((1 + n_docs) / (1 + df_val)) + 1 for term, df_val in df.items()}
    vectors = []
    for tokens in doc_tokens:
        tf = Counter(tokens)
        vec = {term: (count / len(tokens)) * idf[term] for term, count in tf.items()}
        vectors.append(vec)
    return vectors, idf


def cosine_sim(vec_a, vec_b):
    if not vec_a or not vec_b:
        return 0.0
    dot = 0.0
    for term, val in vec_a.items():
        dot += val * vec_b.get(term, 0.0)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def query_to_vec(query, idf):
    tokens = tokenize(query)
    if not tokens:
        return {}
    tf = Counter(tokens)
    return {term: (count / len(tokens)) * idf.get(term, 0.0) for term, count in tf.items()}


def retrieve(query, docs, vectors, idf, top_k=2):
    q_vec = query_to_vec(query, idf)
    scored = []
    for (name, text), vec in zip(docs, vectors):
        scored.append((cosine_sim(q_vec, vec), name, text))
    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[:top_k]


def synthesize_answer(query, passages):
    if not passages:
        return "No relevant context found."
    context = "\n".join(f"[{name}] {text.strip()}" for _, name, text in passages)
    return (
        "Question: " + query + "\n\n" +
        "Context:\n" + context + "\n\n" +
        "Answer (template): Use the context above to answer concisely."
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python rag_simple.py 'your question'")
        sys.exit(1)
    data_dir = Path(__file__).parent / "sample_data"
    docs = load_docs(data_dir)
    vectors, idf = build_tfidf(docs)
    query = " ".join(sys.argv[1:])
    top = retrieve(query, docs, vectors, idf)
    print(synthesize_answer(query, top))


if __name__ == "__main__":
    main()
