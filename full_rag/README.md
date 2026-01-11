# Full RAG Sample (local-first)

A fuller RAG sample with embeddings, FAISS, and optional local LLM.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On macOS, Python 3.12 is recommended to avoid SciPy build errors.

## Ingest

```bash
python ingest.py
```

## Query

```bash
python query.py "What is RAG?"
```

Japanese is supported by default. Ask in Japanese to get Japanese answers.

## Local LLM (optional)

Set `LLAMA_MODEL_PATH` to a GGUF file for llama-cpp-python:

```bash
export LLAMA_MODEL_PATH=/path/to/model.gguf
python query.py "What is RAG?"
```

If no model is set, the script prints top contexts instead of generation.

### Example model (downloaded)

This repo now includes a small GGUF model for testing:

```bash
export LLAMA_MODEL_PATH=models/tinyllama-1.1b-chat.Q4_K_M.gguf
python query.py "What is RAG?"
```

## Agent Mode (LLM can run Python)

This mode lets the LLM request a Python snippet for calculations.

```bash
export LLAMA_MODEL_PATH=models/tinyllama-1.1b-chat.Q4_K_M.gguf
python agent.py "Calculate 12*34 and summarize RAG in one sentence."
```

Note: the Python tool executes code locally. Only run with trusted prompts.

## Power Agent (pandapower + RAG)

This mode lets the LLM request a pandapower power-flow analysis. Results are
saved to `results/` and ingested into the RAG index.

```bash
source .venv/bin/activate
export LLAMA_MODEL_PATH=models/tinyllama-1.1b-chat.Q4_K_M.gguf
python power_agent.py "Run a case14 power flow with load_scale 1.2 and summarize."
```

Supported cases: case9, case14, case30, case118.

Japanese is supported by default in agent mode as well.

## Step-by-step (all demos)

Run the full sequence from a fresh terminal:

```bash
cd /Users/shigenoburyuto/Downloads/RAG_codex
python simple_rag/rag_simple.py "What is RAG?"

cd /Users/shigenoburyuto/Downloads/RAG_codex/full_rag
source .venv/bin/activate
pip install -r requirements.txt
python ingest.py
python query.py "What is RAG?"

export LLAMA_MODEL_PATH=models/tinyllama-1.1b-chat.Q4_K_M.gguf
python agent.py "Calculate 12*34 and summarize RAG in one sentence."
python power_agent.py "Run a case14 power flow with load_scale 1.2 and summarize."
```

## Local Analysis Server (fully local)

This server accepts a question, asks the local LLM to extract requirements,
runs pandapower, and logs outputs to `logs/` while saving results to `results/`.

```bash
cd /Users/shigenoburyuto/Downloads/RAG_codex/full_rag
source .venv/bin/activate
export LLAMA_MODEL_PATH=models/tinyllama-1.1b-chat.Q4_K_M.gguf
python start_server.py
```

If you do not want the browser to auto-open:

```bash
NO_BROWSER=1 python start_server.py
```

The server auto-selects a free port starting from 8000. To set a different base:

```bash
PORT=8100 python start_server.py
```

Example request:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"question":"Run a case14 power flow with load_scale 1.2 and summarize."}'
```

Dry-run (extract requirements only):

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"question":"case14, load_scale 1.2, step_s 0.1, duration_s 10","dry_run":true}'
```
