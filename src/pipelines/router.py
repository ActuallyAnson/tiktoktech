from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Iterable
import json
import pandas as pd

# -----------------------------------------------------------------------------
# Router configuration
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class RouterConfig:
    # NEW: category-only routing (ignore classification/confidence)
    category_only: bool = True

    only_llm: bool = False                 # route only rows categorized by LLM
    llm_domains_col: str = "llm_domains"   # where enrichment wrote domains
    # These are ignored when category_only=True, but kept for compatibility
    min_confidence: float = 0.75
    max_agents_per_item: int = 3
    require_review_labels: Iterable[str] = ("NEEDS HUMAN REVIEW", "REQUIRES REVIEW (rules hint REQUIRED)")

    human_review_agent: str = "HumanReviewAgent"
    default_agent: str = "GeneralComplianceAgent"

# Domain → agent
DOMAIN_TO_AGENT: Dict[str, str] = {
    "Child Safety": "ChildSafetyAgent",
    "Privacy & Data Protection": "PrivacyAgent",
    "Content Moderation / Illegal Content": "ModerationAgent",
    "General Compliance": "GeneralComplianceAgent",
}

# Region overrides (appended)
REGION_AGENT_OVERRIDES: Dict[str, str] = {
    "US-CA": "CaliforniaPrivacyAgent",
    "US-FL": "FloridaMinorsAgent",
    "EU":    "EUComplianceAgent",
    "SG":    "SingaporePDPAAgent",
}

# Columns in enriched CSV
COL_CLASS = "final_classification"
COL_CONF  = "final_confidence"
COL_DOMS  = "final_domains"
COL_REGS  = "final_primary_regions"
COL_PRESCAN_REQUIRED = "prescan_required_hint"
COL_MANUAL_AGENTS = "manual_agents"
COL_SKIP_AGENTS   = "skip_agents"
COL_PRESCAN_BOOST = "prescan_confidence_boost"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _to_list(v) -> List[str]:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        v = v.strip()
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        if v:
            return [v]
    return []

def _unique_keep_order(seq: Iterable[str]) -> List[str]:
    seen, out = set(), []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

# -----------------------------------------------------------------------------
# Core routing logic
# -----------------------------------------------------------------------------
def route_row(row: pd.Series, *, cfg: RouterConfig = RouterConfig()) -> Dict[str, Any]:

    if cfg.only_llm:
        llm_domains = _to_list(row.get(cfg.llm_domains_col))

        try:
            prescan_boost = float(row.get(COL_PRESCAN_BOOST) or 0.0)
        except Exception:
            prescan_boost = 0.0

        if len(llm_domains) == 0 and prescan_boost != 0.0:
            return {
                "agents": [],
                "reason": "skip: no llm_domains and prescan_boost>0",
                "policy": {}
            }
    """
    Returns a routing decision for one item (no LLM calls):
    {
      'agents': ['PrivacyAgent', ...],
      'reason': 'why',
      'policy': {... snapshot ...}
    }
    """
    classification = (row.get(COL_CLASS) or "").strip()
    try:
        confidence = float(row.get(COL_CONF) or 0.0)
    except Exception:
        confidence = 0.0

    domains = _to_list(row.get(COL_DOMS))
    regions = _to_list(row.get(COL_REGS))
    prescan_required = bool(row.get(COL_PRESCAN_REQUIRED, False))

    manual_agents = _to_list(row.get(COL_MANUAL_AGENTS))
    skip_agents   = set(_to_list(row.get(COL_SKIP_AGENTS)))

    # 1) Manual overrides
    if manual_agents:
        agents = [a for a in manual_agents if a not in skip_agents]
        agents = agents[: cfg.max_agents_per_item] or [cfg.human_review_agent]
        return {
            "agents": agents,
            "reason": "manual override",
            "policy": {"domains": domains, "regions": regions}
        }

    # === CATEGORY-ONLY MODE (default) ===
    if cfg.category_only:
        # 2) Domain-based mapping (no confidence/labels considered)
        mapped = [DOMAIN_TO_AGENT[d] for d in domains if d in DOMAIN_TO_AGENT]

        # 3) Region overrides (append)
        for r in regions:
            ao = REGION_AGENT_OVERRIDES.get(r)
            if ao:
                mapped.append(ao)

        # 4) If nothing mapped at all → default
        if not mapped:
            return {
                "agents": [cfg.default_agent],
                "reason": "no domain; default agent",
                "policy": {"domains": domains, "regions": regions}
            }

        # 5) Apply skip/dedupe/cap
        mapped = [a for a in mapped if a not in skip_agents]
        mapped = _unique_keep_order(mapped)[: cfg.max_agents_per_item]
        return {
            "agents": mapped or [cfg.default_agent],
            "reason": "category-only routing",
            "policy": {"domains": domains, "regions": regions}
        }

    # === LEGACY MODE (uses labels/confidence) ===
    if classification in cfg.require_review_labels:
        return {
            "agents": [cfg.human_review_agent],
            "reason": f"classification={classification}",
            "policy": {"domains": domains, "regions": regions, "confidence": confidence}
        }

    if confidence < cfg.min_confidence:
        return {
            "agents": [cfg.human_review_agent],
            "reason": f"low confidence ({confidence:.2f} < {cfg.min_confidence})",
            "policy": {"domains": domains, "regions": regions, "confidence": confidence}
        }

    mapped = [DOMAIN_TO_AGENT[d] for d in domains if d in DOMAIN_TO_AGENT]
    for r in regions:
        ao = REGION_AGENT_OVERRIDES.get(r)
        if ao:
            mapped.append(ao)

    if not mapped and prescan_required:
        return {
            "agents": [cfg.human_review_agent],
            "reason": "prescan hinted requirement but no domain",
            "policy": {"domains": domains, "regions": regions, "confidence": confidence}
        }

    if not mapped:
        return {
            "agents": [cfg.default_agent],
            "reason": "no domain/region override",
            "policy": {"domains": domains, "regions": regions, "confidence": confidence}
        }

    mapped = [a for a in mapped if a not in skip_agents]
    mapped = _unique_keep_order(mapped)[: cfg.max_agents_per_item]
    return {
        "agents": mapped or [cfg.default_agent],
        "reason": "domain/region routing",
        "policy": {"domains": domains, "regions": regions, "confidence": confidence}
    }

def route_dataframe(df: pd.DataFrame, *, cfg: RouterConfig = RouterConfig()) -> pd.DataFrame:
    routes, reasons = [], []
    for _, row in df.iterrows():
        out = route_row(row, cfg=cfg)
        routes.append(out["agents"])
        reasons.append(out["reason"])
    df = df.copy()
    df["route_agents"] = routes
    df["route_reason"] = reasons
    return df

def build_agent_queues(df: pd.DataFrame, agents_col: str = "route_agents") -> Dict[str, List[int]]:
    queues: Dict[str, List[int]] = {}
    for idx, row in df.iterrows():
        for agent in _to_list(row.get(agents_col, [])):
            queues.setdefault(agent, []).append(int(idx))
    return queues
