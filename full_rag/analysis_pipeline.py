import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from config import default_config
from power_analysis import run_power_flow, run_time_series_power_flow, save_result


def _call_llm(prompt):
    script = Path(__file__).parent / "llm_generate.py"
    result = subprocess.run(
        [os.environ.get("PYTHON_BIN", "python"), str(script)],
        input=prompt,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _fallback_params(question):
    case = "case14"
    match = re.search(r"case\s*(\d+)", question, re.IGNORECASE)
    if match:
        candidate = f"case{match.group(1)}"
        if candidate in {"case9", "case14", "case30", "case118"}:
            case = candidate
    load_scale = 1.0
    match = re.search(r"load[_\s-]*scale\s*([0-9]*\.?[0-9]+)", question, re.IGNORECASE)
    if match:
        load_scale = float(match.group(1))
    gen_scale = 1.0
    match = re.search(r"gen[_\s-]*scale\s*([0-9]*\.?[0-9]+)", question, re.IGNORECASE)
    if match:
        gen_scale = float(match.group(1))
    duration_s = 0.0
    match = re.search(r"duration[_\s-]*s\s*([0-9]*\.?[0-9]+)", question, re.IGNORECASE)
    if match:
        duration_s = float(match.group(1))
    step_s = 0.1
    match = re.search(r"step[_\s-]*s\s*([0-9]*\.?[0-9]+)", question, re.IGNORECASE)
    if match:
        step_s = float(match.group(1))
    return {
        "analysis_type": "power_flow",
        "case": case,
        "load_scale": load_scale,
        "gen_scale": gen_scale,
        "duration_s": duration_s,
        "step_s": step_s,
        "note": "fallback",
    }


def plan_requirements(question):
    prompt = (
        "You are a local analyst. Extract requirements for power analysis.\n"
        "Return JSON only with keys:\n"
        "analysis_type: \"power_flow\" or \"time_series\"\n"
        "case: one of case9, case14, case30, case118\n"
        "load_scale: float\n"
        "gen_scale: float\n"
        "duration_s: float (0 for single power flow)\n"
        "step_s: float (time step; recommended 0.1)\n"
        "note: short text\n"
        "If the question requests 0.1-second steps, set analysis_type to time_series.\n"
        "Question:\n"
        f"{question}\n"
    )
    params = _extract_json(_call_llm(prompt))
    if not params:
        params = _fallback_params(question)
    if params.get("step_s", 0.0) and params.get("step_s", 1.0) <= 0.1:
        params["analysis_type"] = "time_series"
    return {
        "analysis_type": params.get("analysis_type", "power_flow"),
        "case": params.get("case", "case14"),
        "load_scale": float(params.get("load_scale", 1.0)),
        "gen_scale": float(params.get("gen_scale", 1.0)),
        "duration_s": float(params.get("duration_s", 0.0)),
        "step_s": float(params.get("step_s", 0.1)),
        "note": str(params.get("note", "")),
    }


def _save_log(cfg, payload):
    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = cfg.logs_dir / f"log_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def analyze_question(question):
    cfg = default_config()
    cfg.results_dir.mkdir(parents=True, exist_ok=True)
    params = plan_requirements(question)

    if params["analysis_type"] == "time_series" and params["duration_s"] > 0:
        summary = run_time_series_power_flow(
            params["case"],
            params["load_scale"],
            params["gen_scale"],
            params["duration_s"],
            params["step_s"],
        )
        extra = [
            "- mode: quasi-static time series (repeated power flow)",
            f"- duration_s: {summary['duration_s']}",
            f"- step_s: {summary['step_s']}",
            f"- steps: {summary['steps']}",
        ]
    else:
        summary = run_power_flow(params["case"], params["load_scale"], params["gen_scale"])
        extra = None

    result_path = save_result(cfg.results_dir, question, params, summary, extra_lines=extra)

    log_payload = {
        "question": question,
        "params": params,
        "summary": summary,
        "result_path": str(result_path),
    }
    log_path = _save_log(cfg, log_payload)

    return {"summary": summary, "result_path": str(result_path), "log_path": str(log_path)}
