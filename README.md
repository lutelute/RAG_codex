# RAG_codex

このリポジトリは、RAG（Retrieval-Augmented Generation）の最小構成例と、より実用寄りの構成例をまとめたものです。

## 構成

- `simple_rag/`  
  最小構成の RAG サンプル（小さなデータとシンプルなスクリプト）。
- `full_rag/`  
  実運用に近い構成の RAG サンプル（インデックス生成、問い合わせ、サーバー起動など）。

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

サーバー起動を試す場合:

```
python start_server.py
```

## 注意事項

- `full_rag/models/` の大型モデルファイル（`.gguf`）や仮想環境は `.gitignore` で除外しています。
- `full_rag/index.faiss` と `full_rag/metadata.json` はサンプルとして同梱しています。

