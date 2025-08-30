from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import json
import pandas as pd
import time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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

class RateLimitedLLM:
    def __init__(self, inner_client, min_interval_sec: float = 1.0, jitter_sec: float = 0.0):
        self.inner = inner_client
        self.min_interval = float(min_interval_sec)
        self.jitter = float(jitter_sec)
        self._lock = threading.Lock()
        self._last = 0.0

    def generate(self, prompt: str):
        # Ensure at least min_interval between calls (global per-process)
        with self._lock:
            now = time.monotonic()
            wait = (self._last + self.min_interval) - now
            if wait > 0:
                time.sleep(wait)
            if self.jitter > 0.0:
                time.sleep(min(self.jitter, 0.250))
            self._last = time.monotonic()
        # delegate
        return self.inner.generate(prompt)

# --- helper: one task per (row, agent) ---
def _run_agent_task(idx, row, agent_name, llm_client, enable_llm_for_llm_categorized, enable_llm_for_all, AGENT_REGISTRY):
    from src.agents.base import AgentVerdict  # local import to avoid import cycles
    AgentCls = AGENT_REGISTRY.get(agent_name)
    if not AgentCls:
        return None

    # was this row LLM-categorized?
    def _to_list(v):
        if isinstance(v, list): return v
        if isinstance(v, str):
            s = v.strip()
            if not s: return []
            if s.startswith("[") and s.endswith("]"):
                import json, ast
                try:
                    return json.loads(s)
                except Exception:
                    try:
                        val = ast.literal_eval(s)
                        if isinstance(val, (list, tuple)):
                            return [str(x) for x in val]
                    except Exception:
                        inner = s.strip("[]")
                        return [p.strip().strip("'").strip('"') for p in inner.split(",") if p.strip().strip("'").strip('"')]
            return [s]
        return []
    llm_categorized = bool(_to_list(row.get("llm_domains", [])))

    use_llm = False
    if enable_llm_for_all:
        use_llm = True
    elif enable_llm_for_llm_categorized and llm_categorized:
        use_llm = True

    agent = AgentCls(llm=llm_client, llm_enabled=use_llm, llm_mode="always")
    verdict: AgentVerdict = agent.check(row)

    feature_name = (row.get("expanded_feature_name")
                    or row.get("input_feature_name")
                    or "")

    return {
        "row_index": idx,
        "agent": verdict.agent,
        "status": verdict.status,
        "score": verdict.score,
        "reasoning": verdict.reasoning,
        "suggestions": verdict.suggestions,
        "domains": row.get("final_domains"),
        "regions": row.get("final_primary_regions"),
        "feature_name": feature_name,
    }

def main(in_csv: str | Path,
         out_csv: str | Path,
         enable_llm_for_llm_categorized: bool = True,
         enable_llm_for_all: bool = False,
         max_workers: int = 8,
         min_llm_interval_sec: float = 1.0,
         llm_jitter_sec: float = 0.0):
    df = pd.read_csv(in_csv)

    # optional LLM client
    llm_client = None
    want_llm = (enable_llm_for_all or enable_llm_for_llm_categorized)
    if want_llm and get_settings and GeminiClient:
        st = get_settings()
        base_client = GeminiClient(api_key=st.gemini_api_key, model_name=st.gemini_model)
        # wrap with global rate limiter: at most 1 request/sec
        llm_client = RateLimitedLLM(base_client, min_interval_sec=min_llm_interval_sec, jitter_sec=llm_jitter_sec)

    tasks = []
    rows_out: List[Dict] = []

    # fan out tasks
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for idx, row in df.iterrows():
            agent_names = row.get("route_agents", [])
            # robust list coercion (reuse your helper)
            agent_names = agent_names if isinstance(agent_names, list) else _to_list(agent_names)
            for agent_name in agent_names:
                tasks.append(ex.submit(
                    _run_agent_task, idx, row, agent_name,
                    llm_client, enable_llm_for_llm_categorized, enable_llm_for_all, AGENT_REGISTRY
                ))

        for fut in as_completed(tasks):
            res = fut.result()
            if res is not None:
                rows_out.append(res)

    # stable ordering for reproducible diffs
    rows_out.sort(key=lambda r: (r["row_index"], r["agent"]))

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows_out).to_csv(out_path, index=False)
    print(f"✓ Wrote agent results → {out_path}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(
        description="Run domain agents in parallel with optional LLM. Use --llm-all to send every routed row to LLM (rate-limited)."
    )
    p.add_argument("--in", dest="in_csv", required=True, help="Input routed CSV")
    p.add_argument("--out", dest="out_csv", required=True, help="Output agent results CSV")
    p.add_argument("--llm-for-llm-categorized", action="store_true",
                   help="Enable LLM only for rows with non-empty llm_domains.")
    p.add_argument("--llm-all", action="store_true",
                   help="Enable LLM for every routed row (ignores llm_domains).")
    p.add_argument("--workers", type=int, default=8, help="Max parallel workers (default 8).")
    p.add_argument("--llm-min-interval", type=float, default=1.0,
                   help="Minimum seconds between LLM requests (default 1.0).")
    p.add_argument("--llm-jitter", type=float, default=0.0,
                   help="Extra jitter seconds to randomize spacing (default 0.0).")
    args = p.parse_args()
    main(args.in_csv, args.out_csv,
         enable_llm_for_llm_categorized=args.llm_for_llm_categorized,
         enable_llm_for_all=args.llm_all,
         max_workers=args.workers,
         min_llm_interval_sec=args.llm_min_interval,
         llm_jitter_sec=args.llm_jitter)