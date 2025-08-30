import pytest
import pandas as pd
from src.utils.merge import merge_prescan_llm

def make_row(required_hint: bool, boost: float = 0.0):
    return pd.Series({
        "prescan_required_hint": required_hint,
        "prescan_domains": '["Child Safety"]' if required_hint else "[]",
        "prescan_primary_regions": "[]",
        "prescan_law_hits": "[]",
        "prescan_confidence_boost": boost,
    })

def test_prescan_required_and_llm_not_required_low_confidence_triggers_review():
    row = make_row(required_hint=True)
    llm_obj = {"classification":"NOT REQUIRED","confidence":0.5,"domains":[]}
    merged = merge_prescan_llm(row, llm_obj, downgrade_guard=0.8)
    assert merged["final_classification"] == "REQUIRES REVIEW (rules hint REQUIRED)"

def test_prescan_required_and_llm_not_required_high_confidence_allows_override():
    row = make_row(required_hint=True)
    llm_obj = {"classification":"NOT REQUIRED","confidence":0.95,"domains":[]}
    merged = merge_prescan_llm(row, llm_obj, downgrade_guard=0.8)
    assert merged["final_classification"] == "NOT REQUIRED"

def test_confidence_boost_applied():
    row = make_row(required_hint=False, boost=0.15)
    llm_obj = {"classification":"REQUIRED","confidence":0.6,"domains":["Privacy & Data Protection"]}
    merged = merge_prescan_llm(row, llm_obj, downgrade_guard=0.8)
    assert merged["final_confidence"] == pytest.approx(0.75, rel=1e-2)
    assert "Privacy & Data Protection" in merged["final_domains"]