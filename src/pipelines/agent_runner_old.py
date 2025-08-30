from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import json
import pandas as pd

from src.agents.child_safety import ChildSafetyAgent
from src.agents.privacy import PrivacyAgent
from src.agents.moderation import ModerationAgent
from src.agents.general import GeneralComplianceAgent
from src.agents.base import AgentVerdict

# Optional: wire in your GeminiClient if you want LLM fallbacks
try:
    from src.config.settings import get_settings
    from src.llm.gemini_client import GeminiClient
except Exception:
    get_settings = None
    GeminiClient = None

AGENT_REGISTRY = {
    "ChildSafetyAgent": ChildSafetyAgent,
    "PrivacyAgent": PrivacyAgent,
    "ModerationAgent": ModerationAgent,
    "GeneralComplianceAgent": GeneralComplianceAgent
    # add others if required
}

def _to_list(v) -> List[str]:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        # JSON first
        if s.startswith("[") and s.endswith("]"):
            import json, ast
            try:
                return json.loads(s)                   # valid JSON -> list[str]
            except Exception:
                try:
                    val = ast.literal_eval(s)          # Python repr -> list
                    if isinstance(val, (list, tuple)):
                        return [str(x) for x in val]
                except Exception:
                    # fallback: naive split
                    inner = s.strip("[]")
                    return [p.strip().strip("'").strip('"')
                            for p in inner.split(",") if p.strip().strip("'").strip('"')]
        # plain string -> single-item list
        return [s]
    return []

def main(in_csv: str | Path, out_csv: str | Path, enable_llm_for_llm_categorized: bool = True):
    df = pd.read_csv(in_csv)

    # Configure optional LLM client (used only on borderline rows)
    llm_client = None
    if enable_llm_for_llm_categorized and get_settings and GeminiClient:
        st = get_settings()
        llm_client = GeminiClient(api_key=st.gemini_api_key, model_name=st.gemini_model)

    rows: List[Dict] = []
    for idx, row in df.iterrows():
        agent_names = _to_list(row.get("route_agents", []))
        # detect if this row was categorized by LLM (i.e., came from NONE set earlier)
        llm_categorized = bool(_to_list(row.get("llm_domains", [])))

        for agent_name in agent_names:
            AgentCls = AGENT_REGISTRY.get(agent_name)
            if not AgentCls:
                continue

            agent = AgentCls(llm=llm_client, llm_enabled=(enable_llm_for_llm_categorized and llm_categorized), llm_mode="always")
            verdict: AgentVerdict = agent.check(row)

            rows.append({
                "row_index": idx,
                "agent": verdict.agent,
                "status": verdict.status,
                "score": verdict.score,
                "reasoning": verdict.reasoning,
                "suggestions": verdict.suggestions,
                # trace: what we routed on
                "domains": row.get("final_domains"),
                "regions": row.get("final_primary_regions"),
                "feature_name": row.get("input_feature_name"),
            })

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"✓ Wrote agent results → {out_path}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Run domain agents (rule-first; optional LLM for borderline cases).")
    p.add_argument("--in", dest="in_csv", required=True, help="Input routed CSV (outputs/llm_routed.csv)")
    p.add_argument("--out", dest="out_csv", required=True, help="Output agent results CSV")
    p.add_argument("--llm-for-llm-categorized", action="store_true",
                   help="Enable LLM fallback ONLY for rows that were categorized by LLM (from domain__NONE.csv).")
    args = p.parse_args()
    main(args.in_csv, args.out_csv, enable_llm_for_llm_categorized=args.llm_for_llm_categorized)
