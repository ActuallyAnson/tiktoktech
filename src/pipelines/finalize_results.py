from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
import argparse
import json
import ast
import pandas as pd

IN_ENRICHED_DEFAULT = "outputs/llm_enriched.csv"
IN_AGENT_DEFAULT = "outputs/agent_results.csv"
OUT_FINAL_DEFAULT = "outputs/final_results.csv"

# ----------------- helpers -----------------
def _to_list(v) -> List[str]:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if s.startswith("[") and s.endswith("]"):
            # try JSON first then Python literal
            try:
                val = json.loads(s)
                if isinstance(val, list):
                    return [str(x) for x in val]
            except Exception:
                try:
                    val = ast.literal_eval(s)
                    if isinstance(val, (list, tuple)):
                        return [str(x) for x in val]
                except Exception:
                    inner = s.strip("[]")
                    return [p.strip().strip("'").strip('"') for p in inner.split(",") if p.strip()]
        return [s]
    return []

def collapse_reasoning(agent_rows: pd.DataFrame) -> str:
    """
    Build a short explanation prioritizing ISSUE -> REVIEW -> OK,
    but keeping it crisp (1-2 lines).
    """
    if agent_rows.empty:
        return "No agent decisions available."
    # Prioritize ISSUE, then REVIEW; include agent names for clarity
    parts: List[str] = []
    for label in ("ISSUE", "REVIEW"):
        sub = agent_rows[agent_rows["status"] == label]
        if not sub.empty:
            names = ", ".join(f"{r['agent']}({r.get('score',0):.2f})" for _, r in sub.iterrows())
            parts.append(f"{label}: {names}")
    if not parts:
        parts.append("All assigned agents returned OK.")
    # Add the first non-empty textual reasoning for color (optional)
    for _, r in agent_rows.iterrows():
        rr = str(r.get("reasoning") or "").strip()
        if rr:
            parts.append(rr)
            break
    # Keep it short
    text = " | ".join(parts)
    return (text[:600] + "…") if len(text) > 600 else text

def pick_final_class(agent_rows: pd.DataFrame) -> str:
    if (agent_rows["status"] == "ISSUE").any():
        return "REQUIRED"
    if (agent_rows["status"] == "REVIEW").any():
        return "NEEDS HUMAN REVIEW"
    return "NOT REQUIRED"

def compute_confidence(agent_rows: pd.DataFrame, final_class: str) -> float:
    # scores are 0..1 provided by agents
    if agent_rows.empty:
        return 0.5
    if final_class == "REQUIRED":
        # strongest indicator
        scores = agent_rows.loc[agent_rows["status"] == "ISSUE", "score"].dropna().astype(float)
        return float(scores.max() if not scores.empty else 0.75)
    if final_class == "NEEDS HUMAN REVIEW":
        scores = agent_rows.loc[agent_rows["status"] == "REVIEW", "score"].dropna().astype(float)
        if scores.empty:
            # borderline with no scores recorded
            return 0.6
        return float(scores.mean())
    # NOT REQUIRED
    return 0.9

# ----------------- main -----------------
def finalize(in_enriched: str, in_agents: str, out_csv: str):
    enr = pd.read_csv(in_enriched)
    ag = pd.read_csv(in_agents)

    # Ensure required columns exist
    for col in ["route_agents", "final_domains", "final_primary_regions", "final_related_regulations",
                "input_feature_name", "input_feature_description",
                "expanded_feature_name", "expanded_feature_description"]:
        if col not in enr.columns:
            enr[col] = None

    # Group agent decisions by row_index (index in enriched CSV)
    if "row_index" not in ag.columns:
        raise ValueError("agent_results.csv must contain 'row_index' produced by agent_runner.")

    grouped: Dict[int, pd.DataFrame] = {int(k): v for k, v in ag.groupby("row_index")}

    records: List[Dict[str, Any]] = []
    for idx, row in enr.iterrows():
        feature = row.get("expanded_feature_name") or row.get("input_feature_name") or ""
        desc    = row.get("expanded_feature_description") or row.get("input_feature_description") or ""

        domains = _to_list(row.get("final_domains"))
        regions = _to_list(row.get("final_primary_regions"))
        regs    = _to_list(row.get("final_related_regulations"))

        agents_df = grouped.get(int(idx), pd.DataFrame(columns=["agent","status","score","reasoning"]))

        # --- NEW: prescan fallback when no agents ran ---
        prescan_required = bool(row.get("prescan_required_hint")) \
                           or len(_to_list(row.get("prescan_law_hits"))) > 0
        prescan_boost = float(row.get("prescan_confidence_boost") or 0.0)
        prescan_rationale = (row.get("prescan_rationale") or "").strip()

        if agents_df.empty and prescan_required:
            final_class = "REQUIRED"
            # base 0.70 + your prescan boost (capped 0.95)
            confidence  = min(0.95, round(0.70 + prescan_boost, 2))
            reasoning   = f"Prescan hard hits. {prescan_rationale or 'Law/domain cues detected.'}"
        else:
            # existing path
            final_class = pick_final_class(agents_df)
            confidence  = round(compute_confidence(agents_df, final_class), 2)
            reasoning   = collapse_reasoning(agents_df)

        records.append({
            "feature": feature,
            "description": desc,
            "domain": ", ".join(domains) if domains else "",
            "primary region": ", ".join(regions) if regions else "",
            "regulation hits": ", ".join(regs) if regs else "",
            "clear reasoning": reasoning,
            "confidence": confidence,
            "Final Classification": final_class,
        })

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(out_path, index=False)
    print(f"✓ Wrote final results → {out_path}  ({len(records)} rows)")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Produce final, audit-ready results table.")
    p.add_argument("--in-enriched", default=IN_ENRICHED_DEFAULT,
                   help="Path to llm_enriched.csv (categorization results)")
    p.add_argument("--in-agents", default=IN_AGENT_DEFAULT,
                   help="Path to agent_results.csv (per-domain agent outcomes)")
    p.add_argument("--out", default=OUT_FINAL_DEFAULT,
                   help="Path to write final results CSV")
    args = p.parse_args()
    finalize(args.in_enriched, args.in_agents, args.out)
