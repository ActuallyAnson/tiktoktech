from dataclasses import dataclass
from typing import Dict, List, Set, Tuple
from .rules_config import LAW_PATTERNS, DOMAIN_PATTERNS, LAW_TO_REGIONS, COMPLIANCE_LANGUAGE, LAW_TO_DOMAINS

@dataclass
class PrescanResult:
    required_hint: bool
    domains: List[str]
    primary_regions: List[str]
    law_hits: List[str]
    keyword_hits: Dict[str, List[str]]   # domain → matched snippets
    rationale: str
    confidence_boost: float

# New: small helper to count all matches and collect snippets
def _find_all_with_snippets(text: str, pattern) -> List[str]:
    out = []
    for m in pattern.finditer(text):
        start = max(0, m.start() - 20)
        end = min(len(text), m.end() + 20)
        out.append(text[start:end])
    return out

def _collect_law_hits(text: str) -> Tuple[Dict[str, int], Set[str]]:
    """Return {law: count} and set(regions)."""
    counts: Dict[str, int] = {}
    regions: Set[str] = set()
    for law, patterns in LAW_PATTERNS.items():
        total = 0
        for p in patterns:
            total += sum(1 for _ in p.finditer(text))
        if total:
            counts[law] = total
            for r in LAW_TO_REGIONS.get(law, []):
                regions.add(r)
    return counts, regions

def _collect_domain_hits(text: str) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    """Return domain -> snippets and domain -> count."""
    hits: Dict[str, List[str]] = {}
    counts: Dict[str, int] = {}
    for domain, patterns in DOMAIN_PATTERNS.items():
        domain_snips = []
        domain_total = 0
        for p in patterns:
            snips = _find_all_with_snippets(text, p)
            domain_snips.extend(snips)
            domain_total += len(snips)
        if domain_total:
            hits[domain] = domain_snips[:8]  # cap snippets for CSV readability
            counts[domain] = domain_total
    return hits, counts

def _has_compliance_language(text: str) -> bool:
    return any(p.search(text) for p in COMPLIANCE_LANGUAGE)

def prescan(feature_name: str, feature_description: str) -> PrescanResult:
    text = f"{feature_name}\n{feature_description}"
    text = " ".join(text.split())

    law_counts, region_hits = _collect_law_hits(text)
    domain_hits, domain_counts = _collect_domain_hits(text)
    compliance = _has_compliance_language(text)

    # Upgrade domain hints from explicit law hits (e.g., SB976 -> Child Safety)
    for law in law_counts.keys():
        for dom in LAW_TO_DOMAINS.get(law, []):
            domain_hits.setdefault(dom, [])
            domain_counts[dom] = max(domain_counts.get(dom, 0), 1)

    # Strong child-safety heuristic: "minor/child/teen" + "age gate/verification/limit/sensitive"
    # (catches your "age-sensitive logic" case)
    import re
    minor = re.search(r"\b(minor|under\s*1[38]|child|teen|kids?)\b", text, re.I) is not None
    age_ctrl = re.search(r"\bage[-\s]*(gate|verification|check|limit|restriction|sensitive)\b", text, re.I) is not None
    if minor and age_ctrl:
        domain_counts["Child Safety"] = max(domain_counts.get("Child Safety", 0), 2)

    required_hint = bool(law_counts) or compliance or (minor and age_ctrl)

    domains = sorted(domain_counts.keys(), key=lambda d: -domain_counts[d])
    primary_regions = sorted(region_hits)
    law_hits = sorted(law_counts.keys())

    # Confidence boost: additive, capped
    boost = 0.0
    if law_counts:
        boost += 0.20          # explicit law stronger than before
    if compliance:
        boost += 0.05
    if minor and age_ctrl:
        boost += 0.10
    boost = min(boost, 0.30)

    # Clearer rationale: list law ids (with counts) + top domains by count
    parts = []
    if law_counts:
        parts.append("laws: " + ", ".join(f"{k}×{v}" for k, v in sorted(law_counts.items())))
    if compliance:
        parts.append("explicit compliance phrasing")
    if domains:
        parts.append("domain hints: " + ", ".join(f"{d}×{domain_counts[d]}" for d in domains[:3]))
    if primary_regions:
        parts.append("regions: " + ", ".join(primary_regions))
    rationale = "; ".join(parts) or "no strong signals"

    return PrescanResult(
        required_hint=required_hint,
        domains=domains,
        primary_regions=primary_regions,
        law_hits=law_hits,
        keyword_hits=domain_hits,   # now contains multiple snippets per domain
        rationale=rationale,
        confidence_boost=boost,
    )
