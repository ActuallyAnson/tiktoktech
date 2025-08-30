from __future__ import annotations
from typing import List, Dict

# DOMAIN_LIST = [
#     "Child Safety","Privacy & Data Protection",
#     "Content Moderation / Illegal Content", "General Compliance"
# ]

# def build_master_prompt(items: List[Dict]) -> str:
#     """
#     items: [{index:int, name:str, desc:str}, ...]
#     """
#     head = f"""You are a geo-regulation compliance router for social media features.
# For EACH feature, return ONE JSON object with:
# - "feature_index": 0-based integer matching the input item,
# - "domains": list from {DOMAIN_LIST},
#   • If the feature clearly matches Child Safety, Privacy & Data Protection, or Content Moderation / Illegal Content, use that domain.
#   • If the feature does NOT clearly fit any of these, use ["General Compliance"].
# - "primary_regions": e.g. ["EU","US-CA","US-FL","US-Federal","SG","BR","CA"],
# - "related_regulations": list of specific laws/acts if implied/mentioned, more preferably [DSA, SB976, HB 3, Utah SMRA, NCMEC].

# Return ONLY a JSON array of these objects (no prose, no markdown fences).
# """
#     body = ["\nFeatures to analyze:\n"]
#     for it in items:
#         body.append(
# f"""=== FEATURE {it['index']} ===
# Name: {it['name'][:2000]}
# Description: {it['desc'][:6000]}
# """)
#     tail = "\nReturn ONLY the JSON array with one object per feature_index."
#     return head + "".join(body) + tail
DOMAIN_LIST = [
    "Child Safety","Privacy & Data Protection",
    "Content Moderation / Illegal Content", "General Compliance"
]

def build_master_prompt(items: List[Dict]) -> str:
    head = f"""You are a geo-regulation compliance router for social media features.
For EACH feature, return ONE JSON object with:
- "feature_index": copy the EXACT integer shown as FEATURE_INDEX (do NOT renumber, do NOT start from 0 unless that exact value is shown).
- "domains": a JSON array chosen from {DOMAIN_LIST}. If none fit, use ["General Compliance"].
- "primary_regions": e.g. ["EU","US-CA","US-FL","US-Federal","SG","BR","CA"] (use [] if unknown),
- "related_regulations": prefer only [DSA, SB976, HB 3, Utah SMRA, NCMEC] (use [] if none).

Return ONLY a JSON array of these objects (no prose, no markdown fences).
"""
    body = ["\nFeatures to analyze:\n"]
    for it in items:
        body.append(
f"""=== FEATURE ===
FEATURE_INDEX: {it['index']}
Name: {it['name'][:2000]}
Description: {it['desc'][:6000]}
""")
    tail = "\nReturn ONLY the JSON array with one object per feature_index."
    return head + "".join(body) + tail