from __future__ import annotations
import json
from pathlib import Path
import argparse
import pandas as pd

from src.pipelines.router import (
    RouterConfig,
    route_dataframe,
    build_agent_queues,
)

def _comma_split(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]

def main():
    p = argparse.ArgumentParser(
        description="Route enriched compliance rows to domain agents (no LLM calls)."
    )
    p.add_argument("--in", dest="in_csv", required=True, help="Input CSV (e.g., outputs/llm_enriched.csv)")
    p.add_argument("--out", dest="out_csv", required=True, help="Output CSV (routed)")
    p.add_argument("--queues-out", dest="queues_json", default=None, help="Optional path to write agent queues JSON")
    p.add_argument("--split-dir", dest="split_dir", default=None, help="Optional folder to write one CSV per agent")

    # Routing mode
    p.add_argument("--category-only", dest="category_only", action="store_true",
                   help="Ignore classification/confidence and route purely by domains/regions (default).")
    p.add_argument("--legacy", dest="use_legacy", action="store_true",
                   help="Use legacy behavior (min-confidence / require-review-labels).")

    p.add_argument("--only-llm", dest="only_llm", action="store_true",
               help="Route only rows that have non-empty llm_domains.")
    # Legacy knobs (ignored when --category-only is used)
    p.add_argument("--min-confidence", type=float, default=0.75, help="(LEGACY) Min confidence else HumanReviewAgent")
    p.add_argument("--max-agents", type=int, default=3, help="Max agents per item (default 3)")
    p.add_argument("--require-review-labels", type=str,
                   default="NEEDS HUMAN REVIEW,REQUIRES REVIEW (rules hint REQUIRED)",
                   help="(LEGACY) Comma-separated labels that force HumanReviewAgent")

    args = p.parse_args()

    in_csv = Path(args.in_csv)
    out_csv = Path(args.out_csv)

    df = pd.read_csv(in_csv)

    # Default to category-only unless --legacy is set
    category_only = True if not args.use_legacy else False
    if args.category_only:
        category_only = True

    cfg = RouterConfig(
        category_only=category_only,
        only_llm=args.only_llm,
        min_confidence=args.min_confidence,
        max_agents_per_item=args.max_agents,
        require_review_labels=tuple(_comma_split(args.require_review_labels)),
    )

    df_routed = route_dataframe(df, cfg=cfg)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_routed.to_csv(out_csv, index=False)
    print(f"✓ Wrote routed CSV → {out_csv}")

    queues = build_agent_queues(df_routed)

    if args.queues_json:
        qpath = Path(args.queues_json)
        qpath.parent.mkdir(parents=True, exist_ok=True)
        with open(qpath, "w", encoding="utf-8") as f:
            json.dump(queues, f, ensure_ascii=False, indent=2)
        print(f"✓ Wrote agent queues JSON → {qpath}")

    if args.split_dir:
        split_dir = Path(args.split_dir)
        split_dir.mkdir(parents=True, exist_ok=True)
        for agent, idxs in queues.items():
            safe = "".join(ch if ch.isalnum() or ch in (" ", "_", "-") else "_" for ch in agent).strip().replace(" ", "_")
            df_agent = df_routed.loc[idxs].copy()
            df_agent.to_csv(split_dir / f"{safe}.csv", index=False)
        print(f"✓ Wrote per-agent CSVs → {split_dir}")

if __name__ == "__main__":
    main()
