#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import default_config
from power_analysis import run_power_flow, save_result
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


def parse_tool_response(text):
    lines = text.strip().splitlines()
    if not lines:
        return ("FINAL", "")
    head = lines[0].strip()
    if head == "PANDAPOWER":
        try:
            end_idx = lines.index("END")
        except ValueError:
            return ("FINAL", text)
        payload = "\n".join(lines[1:end_idx]).strip()
        return ("PANDAPOWER", payload)
    if head == "FINAL":
        return ("FINAL", "\n".join(lines[1:]).strip())
    return ("FINAL", text)


def parse_params_from_text(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def parse_query_fallback(query):
    case = "case14"
    match = re.search(r"case\s*(\d+)", query, re.IGNORECASE)
    if match:
        candidate = f"case{match.group(1)}"
        if candidate in {"case9", "case14", "case30", "case118"}:
            case = candidate
    load_scale = 1.0
    match = re.search(r"load[_\s-]*scale\s*([0-9]*\.?[0-9]+)", query, re.IGNORECASE)
    if match:
        load_scale = float(match.group(1))
    gen_scale = 1.0
    match = re.search(r"gen[_\s-]*scale\s*([0-9]*\.?[0-9]+)", query, re.IGNORECASE)
    if match:
        gen_scale = float(match.group(1))
    return {"case": case, "load_scale": load_scale, "gen_scale": gen_scale, "note": "fallback"}


def parse_query_hints(query):
    return {
        "has_case": bool(re.search(r"case\s*\d+", query, re.IGNORECASE)),
        "has_load_scale": bool(
            re.search(r"load[_\s-]*scale\s*[0-9]*\.?[0-9]+", query, re.IGNORECASE)
        ),
        "has_gen_scale": bool(
            re.search(r"gen[_\s-]*scale\s*[0-9]*\.?[0-9]+", query, re.IGNORECASE)
        ),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python power_agent.py 'your question'")
        sys.exit(1)

    if not os.environ.get("LLAMA_MODEL_PATH"):
        print("LLAMA_MODEL_PATH is not set. Agent mode requires a local LLM.")
        sys.exit(1)

    cfg = default_config()
    if not cfg.index_path.exists() or not cfg.metadata_path.exists():
        print("Index not found. Running ingest...")
        subprocess.run([sys.executable, "ingest.py"], cwd=Path(__file__).parent)

    query = " ".join(sys.argv[1:])
    contexts = retrieve_contexts(query, cfg)
    context_text = "\n".join(contexts)

    system_prompt = (
        "You are a local RAG power-system agent.\n"
        "If a power-flow analysis is needed, request the pandapower tool. "
        "If the question is in Japanese, answer in Japanese.\n\n"
        "Respond in one of these exact formats ONLY:\n"
        "PANDAPOWER\n"
        "{\"case\":\"case14\",\"load_scale\":1.0,\"gen_scale\":1.0,\"note\":\"why\"}\n"
        "END\n"
        "or\n"
        "FINAL\n<answer>\n"
        "Do not add any extra text.\n\n"
        "Supported cases: case9, case14, case30, case118."
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

    params = None
    if mode == "PANDAPOWER":
        params = parse_params_from_text(payload) or None
    fallback = parse_query_fallback(query)
    hints = parse_query_hints(query)
    if hints["has_case"] or hints["has_load_scale"] or hints["has_gen_scale"]:
        params = fallback
    elif params is None:
        params = fallback

    params = {
        "case": params.get("case", "case14"),
        "load_scale": float(params.get("load_scale", 1.0)),
        "gen_scale": float(params.get("gen_scale", 1.0)),
        "note": str(params.get("note", "")),
    }

    if mode == "PANDAPOWER" or params.get("note") == "fallback":
        try:
            summary = run_power_flow(
                params["case"], params["load_scale"], params["gen_scale"]
            )
        except Exception as exc:
            print(f"Power-flow failed: {exc}")
            sys.exit(1)

        result_path = save_result(cfg.results_dir, query, params, summary)
        subprocess.run([sys.executable, "ingest.py"], cwd=Path(__file__).parent)

        tool_output = (
            f"Result saved to {result_path.name}. Summary: "
            f"converged={summary['converged']}, "
            f"load_mw={summary['total_load_mw']}, "
            f"gen_mw={summary['total_gen_mw']}, "
            f"losses_mw={summary['losses_mw']}, "
            f"vmin/vmax={summary['vmin_pu']}/{summary['vmax_pu']}, "
            f"max_line_loading={summary['max_line_loading_percent']}."
        )

        summary_lines = [
            "Pandapower result:",
            f"- case: {params['case']}",
            f"- load_scale: {params['load_scale']}",
            f"- gen_scale: {params['gen_scale']}",
            f"- converged: {summary['converged']}",
            f"- total_load_mw: {summary['total_load_mw']}",
            f"- total_gen_mw: {summary['total_gen_mw']}",
            f"- losses_mw: {summary['losses_mw']}",
            f"- vmin/vmax_pu: {summary['vmin_pu']}/{summary['vmax_pu']}",
            f"- max_line_loading_percent: {summary['max_line_loading_percent']}",
            f"- saved: {result_path.name}",
            "- rag: index updated",
        ]

        if os.environ.get("POWER_AGENT_LLM_SUMMARY") == "1":
            followup = (
                system_prompt
                + "\n\nContext:\n"
                + context_text
                + "\n\nQuestion: "
                + query
                + "\n\nPandapower output:\n"
                + tool_output
                + "\n\nAnswer:"
            )
            response = call_llm(followup)
            mode, payload = parse_tool_response(response)
            if mode != "FINAL":
                payload = response
            if payload:
                summary_lines.append("")
                summary_lines.append("LLM summary:")
                summary_lines.append(payload)

        print("\n".join(summary_lines))
        return

    if mode != "FINAL":
        payload = response
    print(payload)


if __name__ == "__main__":
    main()
