import json
from datetime import datetime
from pathlib import Path


def run_power_flow(case_name, load_scale, gen_scale):
    try:
        import pandapower as pp
        import pandapower.networks as pn
    except Exception as exc:
        raise RuntimeError(f"pandapower import failed: {exc}") from exc

    cases = {
        "case9": pn.case9,
        "case14": pn.case14,
        "case30": pn.case30,
        "case118": pn.case118,
    }
    if case_name not in cases:
        raise ValueError(f"Unsupported case: {case_name}")

    net = cases[case_name]()
    if load_scale != 1.0 and not net.load.empty:
        net.load["p_mw"] = net.load["p_mw"] * load_scale
        net.load["q_mvar"] = net.load["q_mvar"] * load_scale
    if gen_scale != 1.0 and not net.gen.empty:
        net.gen["p_mw"] = net.gen["p_mw"] * gen_scale
    if gen_scale != 1.0 and hasattr(net, "sgen") and not net.sgen.empty:
        net.sgen["p_mw"] = net.sgen["p_mw"] * gen_scale

    pp.runpp(net)

    total_load = float(net.res_load.p_mw.sum()) if not net.res_load.empty else 0.0
    total_gen = 0.0
    if hasattr(net, "res_gen") and not net.res_gen.empty:
        total_gen += float(net.res_gen.p_mw.sum())
    if hasattr(net, "res_sgen") and not net.res_sgen.empty:
        total_gen += float(net.res_sgen.p_mw.sum())
    if hasattr(net, "res_ext_grid") and not net.res_ext_grid.empty:
        total_gen += float(net.res_ext_grid.p_mw.sum())

    losses = 0.0
    if hasattr(net, "res_line") and not net.res_line.empty:
        losses += float(net.res_line.pl_mw.sum())
    if hasattr(net, "res_trafo") and not net.res_trafo.empty:
        losses += float(net.res_trafo.pl_mw.sum())

    vmin = float(net.res_bus.vm_pu.min())
    vmax = float(net.res_bus.vm_pu.max())
    max_loading = None
    top_lines = []
    if hasattr(net, "res_line") and not net.res_line.empty:
        max_loading = float(net.res_line.loading_percent.max())
        top = net.res_line.loading_percent.sort_values(ascending=False).head(5)
        top_lines = [(int(idx), float(val)) for idx, val in top.items()]

    summary = {
        "case": case_name,
        "converged": bool(getattr(net, "converged", True)),
        "total_load_mw": round(total_load, 4),
        "total_gen_mw": round(total_gen, 4),
        "losses_mw": round(losses, 4),
        "vmin_pu": round(vmin, 4),
        "vmax_pu": round(vmax, 4),
        "max_line_loading_percent": round(max_loading, 4) if max_loading is not None else None,
        "top_lines": top_lines,
    }
    return summary


def run_time_series_power_flow(case_name, load_scale, gen_scale, duration_s, step_s):
    if step_s <= 0:
        raise ValueError("step_s must be > 0")
    steps = int(duration_s / step_s) + 1
    vmins = []
    vmaxs = []
    max_loadings = []
    loads = []
    gens = []
    losses = []
    converged = True

    for _ in range(steps):
        summary = run_power_flow(case_name, load_scale, gen_scale)
        converged = converged and summary["converged"]
        vmins.append(summary["vmin_pu"])
        vmaxs.append(summary["vmax_pu"])
        if summary["max_line_loading_percent"] is not None:
            max_loadings.append(summary["max_line_loading_percent"])
        loads.append(summary["total_load_mw"])
        gens.append(summary["total_gen_mw"])
        losses.append(summary["losses_mw"])

    return {
        "case": case_name,
        "converged": converged,
        "steps": steps,
        "duration_s": duration_s,
        "step_s": step_s,
        "total_load_mw": round(max(loads), 4) if loads else 0.0,
        "total_gen_mw": round(max(gens), 4) if gens else 0.0,
        "losses_mw": round(max(losses), 4) if losses else 0.0,
        "vmin_pu": round(min(vmins), 4) if vmins else 0.0,
        "vmax_pu": round(max(vmaxs), 4) if vmaxs else 0.0,
        "max_line_loading_percent": round(max(max_loadings), 4) if max_loadings else None,
    }


def save_result(results_dir, question, params, summary, extra_lines=None):
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"result_{stamp}.md"
    path = results_dir / filename

    lines = [
        "# Pandapower Result",
        "",
        f"- Timestamp (UTC): {stamp}",
        f"- Question: {question}",
        f"- Case: {params['case']}",
        f"- load_scale: {params['load_scale']}",
        f"- gen_scale: {params['gen_scale']}",
        f"- Converged: {summary['converged']}",
        f"- Total load (MW): {summary['total_load_mw']}",
        f"- Total generation (MW): {summary['total_gen_mw']}",
        f"- Losses (MW): {summary['losses_mw']}",
        f"- Vmin/Vmax (pu): {summary['vmin_pu']} / {summary['vmax_pu']}",
        f"- Max line loading (%): {summary['max_line_loading_percent']}",
        "",
        "## Top Loaded Lines",
        "",
    ]
    if summary["top_lines"]:
        for line_id, loading in summary["top_lines"]:
            lines.append(f"- line {line_id}: {loading:.2f}%")
    else:
        lines.append("- (no line data)")

    lines.extend(
        [
            "",
            "## Parameters",
            "```json",
            json.dumps(params, indent=2),
            "```",
        ]
    )
    if extra_lines:
        lines.extend(["", "## Notes"] + extra_lines)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
