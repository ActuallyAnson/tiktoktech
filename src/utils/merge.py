from __future__ import annotations
from typing import Any, Dict, List
import json

def _to_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return []
    return []

def _merge_unique(a: List[str], b: List[str]) -> List[str]:
    return sorted({*(a or []), *(b or [])})

def _coerce_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def merge_prescan_llm(row, llm_obj, downgrade_guard: float):
    pre_required = bool(row.get("prescan_required_hint", False))
    pre_domains  = _to_list(row.get("prescan_domains", []))
    pre_regions  = _to_list(row.get("prescan_primary_regions", []))
    pre_laws     = _to_list(row.get("prescan_law_hits", []))
    pre_boost    = _coerce_float(row.get("prescan_confidence_boost", 0.0))

    llm_class   = (llm_obj or {}).get("classification")
    llm_conf    = _coerce_float((llm_obj or {}).get("confidence", 0.0))
    llm_domains = _to_list((llm_obj or {}).get("domains", []))
    llm_regions = _to_list((llm_obj or {}).get("primary_regions", []))
    llm_regs    = _to_list((llm_obj or {}).get("related_regulations", []))

    final_domains = _merge_unique(pre_domains, llm_domains)
    final_regions = _merge_unique(pre_regions, llm_regions)
    final_regs    = _merge_unique(pre_laws, llm_regs)
    final_conf    = round(min(llm_conf + pre_boost, 0.99), 2)

    final_class = llm_class or ("NEEDS HUMAN REVIEW" if not final_domains else "REQUIRED")
    if pre_required and (llm_class == "NOT REQUIRED") and (llm_conf < downgrade_guard):
        final_class = "REQUIRES REVIEW (rules hint REQUIRED)"

    return {
        "llm_classification": llm_class,
        "llm_confidence": llm_conf,
        "llm_domains": llm_domains,
        "llm_primary_regions": llm_regions,
        "llm_related_regulations": llm_regs,
        "final_domains": final_domains,
        "final_primary_regions": final_regions,
        "final_related_regulations": final_regs,
        "final_confidence": final_conf,
        "final_classification": final_class,
    }

def _cat_to_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return []
    return []

def _cat_merge_unique(a: List[str], b: List[str]) -> List[str]:
    return sorted({*(a or []), *(b or [])})

def merge_categories_only(row: "pd.Series", llm_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Union prescan categories with LLM categories; do not set classification/confidence."""
    pre_domains = _cat_to_list(row.get("prescan_domains", []))
    pre_regions = _cat_to_list(row.get("prescan_primary_regions", []))
    pre_laws    = _cat_to_list(row.get("prescan_law_hits", []))

    llm_domains = _cat_to_list((llm_obj or {}).get("domains", []))
    llm_regions = _cat_to_list((llm_obj or {}).get("primary_regions", []))
    llm_regs    = _cat_to_list((llm_obj or {}).get("related_regulations", []))

    final_domains = _cat_merge_unique(pre_domains, llm_domains)
    final_regions = _cat_merge_unique(pre_regions, llm_regions)
    final_regs    = _cat_merge_unique(pre_laws, llm_regs)

    return {
        # we still expose what LLM suggested for traceability
        "llm_domains": llm_domains or None,
        "llm_primary_regions": llm_regions or None,
        "llm_related_regulations": llm_regs or None,
        # final unions used by the router
        "final_domains": final_domains,
        "final_primary_regions": final_regions,
        "final_related_regulations": final_regs,
        # IMPORTANT: do NOT set final_classification/final_confidence here
    }