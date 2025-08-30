from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from src.config.settings import get_settings
from src.llm.gemini_client import GeminiClient
from src.prompts.enrichment_master import build_master_prompt
from src.utils.json_parser import strict_json_array
from src.utils.merge import merge_prescan_llm

def _to_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return []
    return []

def enrich_ambiguous_with_llm(
    prescan_csv: str | Path,
    out_csv: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Only send ambiguous rows to LLM:
      - no prescan domains OR prescan_required_hint == False
    Keep feature_index as original df index so we can merge cleanly.
    """
    prescan_csv = Path(prescan_csv)
    df = pd.read_csv(prescan_csv)

    needed = [
        "input_feature_name","input_feature_description",
        "expanded_feature_name","expanded_feature_description",
        "prescan_required_hint","prescan_domains","prescan_primary_regions",
        "prescan_law_hits","prescan_confidence_boost"
    ]
    miss = [c for c in needed if c not in df.columns]
    if miss:
        raise ValueError(f"Missing required columns in prescan CSV: {miss}")

    # Decide ambiguity (gate)
    has_domains = df["prescan_domains"].apply(lambda x: len(_to_list(x)) > 0)
    ambiguous_mask = (~has_domains) | (df["prescan_required_hint"] == False)
    amb_df = df[ambiguous_mask].copy()

    # Prepare LLM inputs ONLY for ambiguous rows (use expanded fields if present)
    items: List[Dict[str, Any]] = []
    for idx, r in amb_df.iterrows():
        name = r.get("expanded_feature_name") or r.get("input_feature_name") or ""
        desc = r.get("expanded_feature_description") or r.get("input_feature_description") or ""
        items.append({"index": int(idx), "name": str(name), "desc": str(desc)})

    settings = get_settings()
    client = GeminiClient(api_key=settings.gemini_api_key, model_name=settings.gemini_model)

    if items:
        prompt = build_master_prompt(items)
        raw_text = client.generate(prompt)
        try:
            arr = strict_json_array(raw_text)
        except Exception as e:
            dump_path = prescan_csv.parent / "llm_raw_response.txt"
            dump_path.write_text(raw_text, encoding="utf-8")
            raise RuntimeError(f"LLM response parsing failed: {e}. Raw text saved to {dump_path}")
        by_index: Dict[int, Dict[str, Any]] = {
            obj.get("feature_index"): obj for obj in arr if isinstance(obj.get("feature_index"), int)
        }
    else:
        by_index = {}

    # Ensure destination columns exist
    new_cols = [
        "llm_classification","llm_confidence",
        "llm_domains","llm_primary_regions","llm_related_regulations",
        "final_domains","final_primary_regions","final_related_regulations",
        "final_confidence","final_classification"
    ]
    for c in new_cols:
        if c not in df.columns:
            df[c] = None

    # Merge: for ambiguous rows use LLM+prescan; otherwise carry prescan forward
    for idx, row in df.iterrows():
        if idx in by_index:
            merged = merge_prescan_llm(row, by_index[idx], settings.confidence_downgrade_guard)
        else:
            # Non-ambiguous → keep prescan as final, with a sensible confidence default
            prescan_domains = _to_list(row.get("prescan_domains", []))
            prescan_regions = _to_list(row.get("prescan_primary_regions", []))
            prescan_laws    = _to_list(row.get("prescan_law_hits", []))
            boost = float(row.get("prescan_confidence_boost", 0.0) or 0.0)
            merged = {
                "llm_classification": None,
                "llm_reasoning": None,
                "llm_confidence": None,
                "llm_domains": None,
                "llm_primary_regions": None,
                "llm_related_regulations": None,
                "final_domains": prescan_domains,
                "final_primary_regions": prescan_regions,
                "final_related_regulations": prescan_laws,
                "final_confidence": round(min(0.75 + boost, 0.95), 2),  # conservative default
                "final_classification": "REQUIRED" if bool(row.get("prescan_required_hint", False)) else "NOT REQUIRED",
            }
        for k, v in merged.items():
            df.at[idx, k] = v

    # Optional write: lists → JSON strings
    if out_csv:
        out_csv = Path(out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        list_cols = ["llm_domains","llm_primary_regions","llm_related_regulations",
                     "final_domains","final_primary_regions","final_related_regulations"]
        to_write = df.copy()
        for c in list_cols:
            to_write[c] = to_write[c].apply(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else (v if v is not None else "[]"))
        to_write.to_csv(out_csv, index=False)
        print(f"Wrote enriched results → {out_csv}")

    return df

if __name__ == "__main__":
    # Example:
    # python -m src.pipelines.llm_enrichment --prescan outputs/prescan_results.csv --out outputs/llm_enriched.csv
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--prescan", required=True, help="Path to prescan_results.csv")
    p.add_argument("--out", required=True, help="Output CSV path")
    args = p.parse_args()
    enrich_ambiguous_with_llm(args.prescan, args.out)