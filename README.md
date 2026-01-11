# RAG_codex

このリポジトリは、RAG（Retrieval-Augmented Generation）の最小構成例と、より実用寄りの構成例をまとめたものです。

## 構成

- `simple_rag/`  
  最小構成の RAG サンプル（小さなデータとシンプルなスクリプト）。
- `full_rag/`  
  実運用に近い構成の RAG サンプル（インデックス生成、問い合わせ、サーバー起動など）。

## 仕様概要

- `simple_rag` は Python 標準ライブラリのみで動作する最小 RAG（TF-IDF + コサイン類似度）。
- `full_rag` は埋め込み + FAISS による検索を行い、ローカル LLM（llama-cpp-python）を任意で利用可能。
- `full_rag/agent.py` は LLM が Python 実行を要求できるエージェントモード（ローカル実行）。
- `full_rag/power_agent.py` は pandapower による潮流解析を実行し、結果を `results/` に保存してインデックスへ取り込み。
- `full_rag/server.py` / `start_server.py` はローカル分析サーバー（`/analyze` エンドポイント）を起動。

## 使い方（概要）

### simple_rag

```
cd simple_rag
python rag_simple.py
```

### full_rag

```
cd full_rag
python ingest.py
python query.py
```

ローカル LLM を使う場合:

```
export LLAMA_MODEL_PATH=/path/to/model.gguf
python query.py "What is RAG?"
```

サーバー起動を試す場合:

```
python start_server.py
```

## 依存関係メモ

- `full_rag/` は `requirements.txt` を使用（macOS では Python 3.12 推奨）。
- LLM を使わない場合は、検索結果の上位コンテキストのみ出力。

## 注意事項

- `full_rag/models/` の大型モデルファイル（`.gguf`）や仮想環境は `.gitignore` で除外しています。
- `full_rag/index.faiss` と `full_rag/metadata.json` はサンプルとして同梱しています。
