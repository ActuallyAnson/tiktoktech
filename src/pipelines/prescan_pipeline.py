# src/tools/prescan_pipeline.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd

# Import your existing helpers
from src.processors.text_preprocessor import expand_terminology  # uses optional terminology arg
from src.processors.prescan import prescan         # deterministic classifier

def load_terminology_json(path: str | Path) -> Dict[str, str]:
    """Load a terminology mapping JSON: { "ASL": "Age Sensitive Logic", ... }."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def expand_fields(name: str, desc: str, terminology: Dict[str, str]) -> tuple[str, str, str]:
    """Return (merged_original, expanded_name, expanded_desc)."""
    # Expand each field separately so you can keep them split in outputs
    exp_name = expand_terminology(name or "", terminology)  # uses your regex word-boundaries
    exp_desc = expand_terminology(desc or "", terminology)
    merged = f"{exp_name}\n{exp_desc}".strip()
    return merged, exp_name, exp_desc

def process_csv_with_prescan(
    input_csv: str | Path,
    terminology_json: str | Path,
    out_csv: Optional[str | Path] = None,
    split_by_domain_dir: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Read CSV -> expand terminology -> prescan -> organize.

    Args:
        input_csv: path to CSV with columns: feature_name, feature_description
        terminology_json: path to JSON terminology map
        out_csv: optional path to write consolidated results
        split_by_domain_dir: optional folder to write one CSV per domain

    Returns:
        Pandas DataFrame of results (one row per input feature).
    """
    input_csv = Path(input_csv)
    terminology_json = Path(terminology_json)

    # 1) Load inputs
    df = pd.read_csv(input_csv)
    required_cols = ["feature_name", "feature_description"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    terminology = load_terminology_json(terminology_json)

    # 2) Expand + Prescan
    rows: List[Dict[str, Any]] = []
    for i, row in df.iterrows():
        name = str(row["feature_name"]) if pd.notna(row["feature_name"]) else ""
        desc = str(row["feature_description"]) if pd.notna(row["feature_description"]) else ""

        merged_expanded, exp_name, exp_desc = expand_fields(name, desc, terminology)

        # prescan on the expanded text (keep name/desc separate for audit)
        ps = prescan(exp_name, exp_desc)      # or prescan_dict if you prefer a flat dict

        # Structure a single record for output
        rows.append({
            "input_feature_name": name,
            "input_feature_description": desc,
            "expanded_feature_name": exp_name,
            "expanded_feature_description": exp_desc,
            "prescan_required_hint": ps.required_hint,
            "prescan_domains": ps.domains,                         # list
            "prescan_primary_regions": ps.primary_regions,         # list
            "prescan_law_hits": ps.law_hits,                       # list
            "prescan_rationale": ps.rationale,
            "prescan_confidence_boost": ps.confidence_boost,
            "prescan_keyword_hits": ps.keyword_hits,               # dict: domain -> [snippets]
        })

    results = pd.DataFrame(rows)

    # 3) Optional: write consolidated CSV
    if out_csv:
        out_csv = Path(out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        # Convert lists/dicts to JSON strings for safe CSV storage
        json_cols = ["prescan_domains", "prescan_primary_regions", "prescan_law_hits", "prescan_keyword_hits"]
        to_write = results.copy()
        for c in json_cols:
            to_write[c] = to_write[c].apply(lambda v: json.dumps(v, ensure_ascii=False))
        to_write.to_csv(out_csv, index=False)

    # 4) Optional: split by domain and write one CSV per category
    if split_by_domain_dir:
        split_dir = Path(split_by_domain_dir)
        split_dir.mkdir(parents=True, exist_ok=True)

        # explode rows across multiple domains so one feature can land in several files
        exploded = results.explode("prescan_domains")
        exploded = exploded.rename(columns={"prescan_domains": "domain"})
        # Separate items with no domain (NaN after explode)
        no_domain_df = exploded[exploded["domain"].isna()].copy()
        if not no_domain_df.empty:
            no_domain_df.to_csv(split_dir / "domain__NONE.csv", index=False)

        # Write one CSV per domain
        for domain, group in exploded.dropna(subset=["domain"]).groupby("domain"):
            safe = "".join(ch if ch.isalnum() or ch in (" ", "_", "-") else "_" for ch in domain).strip().replace(" ", "_")
            group.to_csv(split_dir / f"domain__{safe}.csv", index=False)

    return results

if __name__ == "__main__":
    # Example CLI usage:
    # python -m src.tools.prescan_pipeline \
    #   --input data/sample_features.csv \
    #   --terms data/terminology.json \
    #   --out outputs/prescan_results.csv \
    #   --split outputs/by_domain
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to input CSV with 'feature_name','feature_description'")
    p.add_argument("--terms", required=True, help="Path to terminology JSON")
    p.add_argument("--out", default=None, help="Optional consolidated CSV output path")
    p.add_argument("--split", default=None, help="Optional folder to write per-domain CSVs")
    args = p.parse_args()

    df_out = process_csv_with_prescan(args.input, args.terms, args.out, args.split)
    print(f"Processed {len(df_out)} rows.")
