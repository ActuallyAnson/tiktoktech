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
from src.utils.merge import merge_categories_only

# --- helpers ------------------------------------------------------------
def _to_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return []
    return []

def _make_join_key(df: pd.DataFrame) -> pd.Series:
    # Use expanded fields if available; fall back to input fields
    name = df.get("expanded_feature_name", df.get("input_feature_name")).fillna("")
    desc = df.get("expanded_feature_description", df.get("input_feature_description")).fillna("")
    return (name.astype(str) + "||" + desc.astype(str)).astype(str)

# --- main ---------------------------------------------------------------
def enrich_none_only(
    prescan_csv: str | Path,
    none_csv: str | Path,
    out_csv: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Load full prescan results + the by_domain/domain__NONE.csv,
    call LLM ONLY for those 'NONE' rows, merge results back,
    and write an enriched CSV.
    """
    prescan_csv = Path(prescan_csv)
    none_csv = Path(none_csv)

    df_all = pd.read_csv(prescan_csv)
    df_none = pd.read_csv(none_csv)

    # Validate required columns that prescan produces
    needed = [
        "input_feature_name","input_feature_description",
        "expanded_feature_name","expanded_feature_description",
        "prescan_required_hint","prescan_domains","prescan_primary_regions",
        "prescan_law_hits","prescan_confidence_boost",
    ]
    missing = [c for c in needed if c not in df_all.columns]
    if missing:
        raise ValueError(f"Missing required columns in prescan CSV: {missing}")

    # Try to align NONE rows back to master by a stable join key.
    # (If you previously saved a row_id, merge on that instead.)
    if "row_id" in df_all.columns and "row_id" in df_none.columns:
        key_all = "row_id"
        df_all[key_all] = df_all[key_all].astype(int)
        df_none[key_all] = df_none[key_all].astype(int)
        none_ids = set(df_none[key_all].tolist())
        target_idx = df_all.index[df_all[key_all].isin(none_ids)].tolist()
    else:
        df_all["_join_key"] = _make_join_key(df_all)
        df_none["_join_key"] = _make_join_key(df_none)
        none_keys = set(df_none["_join_key"].tolist())
        target_idx = df_all.index[df_all["_join_key"].isin(none_keys)].tolist()

    # Build items for LLM from the subset only
    items: List[Dict[str, Any]] = []
    for idx in target_idx:
        r = df_all.loc[idx]
        name = r.get("expanded_feature_name") or r.get("input_feature_name") or ""
        desc = r.get("expanded_feature_description") or r.get("input_feature_description") or ""
        items.append({"index": int(idx), "name": str(name), "desc": str(desc)})

    # Call Gemini once for the subset (classification-only contract)
    settings = get_settings()
    client = GeminiClient(api_key=settings.gemini_api_key, model_name=settings.gemini_model)

    by_index: Dict[int, Dict[str, Any]] = {}
    if items:
        prompt = build_master_prompt(items)
        raw_text = client.generate(prompt)
        try:
            arr = strict_json_array(raw_text)
        except Exception as e:
            dump_path = prescan_csv.parent / "llm_raw_response.txt"
            dump_path.write_text(raw_text, encoding="utf-8")
            raise RuntimeError(f"LLM response parsing failed: {e}. Raw text saved to {dump_path}")
        by_index = {obj.get("feature_index"): obj for obj in arr if isinstance(obj.get("feature_index"), int)}

    # Ensure destination columns exist
    new_cols = [
        "llm_domains","llm_primary_regions","llm_related_regulations",
        "final_domains","final_primary_regions","final_related_regulations",
    ]
    for c in new_cols:
        if c not in df_all.columns:
            df_all[c] = None

    # Merge LLM categories for NONE rows; carry prescan forward for others if still empty
    for idx, row in df_all.iterrows():
        if idx in by_index:
            merged = merge_categories_only(row, by_index[idx])   # <-- category-only merge
        else:
            # If not in NONE subset, keep prescan-derived finals if they exist; otherwise seed from prescan
            prescan_domains = _to_list(row.get("prescan_domains", []))
            prescan_regions = _to_list(row.get("prescan_primary_regions", []))
            prescan_laws    = _to_list(row.get("prescan_law_hits", []))
            merged = {
                "llm_domains": row.get("llm_domains"),
                "llm_primary_regions": row.get("llm_primary_regions"),
                "llm_related_regulations": row.get("llm_related_regulations"),
                "final_domains": row.get("final_domains") or prescan_domains,
                "final_primary_regions": row.get("final_primary_regions") or prescan_regions,
                "final_related_regulations": row.get("final_related_regulations") or prescan_laws,
            }
        for k, v in (merged or {}).items():
            df_all.at[idx, k] = v

    # Write out (lists → JSON strings so CSV stays readable)
    if out_csv:
        out_csv = Path(out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        list_cols = ["llm_domains","llm_primary_regions","llm_related_regulations",
                     "final_domains","final_primary_regions","final_related_regulations"]
        to_write = df_all.copy()
        for c in list_cols:
            to_write[c] = to_write[c].apply(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else (v if v is not None else "[]"))
        to_write.to_csv(out_csv, index=False)
        print(f"Wrote enriched results → {out_csv}")

    # Clean temp join key if we added it
    if "_join_key" in df_all.columns:
        del df_all["_join_key"]

    return df_all

if __name__ == "__main__":
    # Example:
    # python -m src.pipelines.llm_enrichment_none \
    #   --prescan outputs/prescan_results.csv \
    #   --none outputs/by_domain/domain__NONE.csv \
    #   --out outputs/llm_enriched.csv
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--prescan", required=True, help="Path to prescan_results.csv")
    p.add_argument("--none", required=True, help="Path to by_domain/domain__NONE.csv")
    p.add_argument("--out", required=True, help="Output CSV path")
    args = p.parse_args()
    enrich_none_only(args.prescan, args.none, args.out)
