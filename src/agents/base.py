from dataclasses import dataclass
from typing import Dict, Any, Optional
import re
import json, re, time
from typing import Iterable, Optional, Dict, Any, List, Tuple

@dataclass
class AgentVerdict:
    agent: str
    status: str                  # "OK" | "ISSUE" | "REVIEW"
    score: float                 # 0..1 checklist score
    reasoning: str
    suggestions: Optional[str] = None

class BaseAgent:
    name: str = "BaseAgent"
    domain: str = "General"

    def __init__(self, llm=None, llm_enabled: bool = False, llm_mode: str = "review_only"):
        self.llm = llm
        self.llm_enabled = llm_enabled
        # NEW: "always" | "review_only"
        self.llm_mode = llm_mode

    @staticmethod
    def text(row) -> str:
        name = (row.get("expanded_feature_name") or row.get("input_feature_name") or "")
        desc = (row.get("expanded_feature_description") or row.get("input_feature_description") or "")
        return f"{name}\n{desc}"

    @staticmethod
    def has(pattern: str, text: str) -> bool:
        return re.search(pattern, text, flags=re.I) is not None

    def llm_json(self, prompt: str, *,
                 expect_keys: Iterable[str] = ("status","reasoning"),
                 retries: int = 2) -> Optional[Dict[str, Any]]:
        """
        Call the LLM and robustly parse a SINGLE JSON object.
        Assumes your Gemini client is set to response_mime_type='application/json'.
        """
        if not (self.llm and self.llm_enabled):
            return None

        def _parse(raw: str) -> Optional[Dict[str, Any]]:
            raw = (raw or "").strip()
            # strip ```json fences if any
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I|re.M)
            # try direct JSON
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
            # try first {...} block
            m = re.search(r"\{.*\}", raw, flags=re.S)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    pass
            return None

        ask = prompt
        for _ in range(retries + 1):
            raw = self.llm.generate(ask)
            obj = _parse(raw)
            if obj and all(k in obj for k in expect_keys):
                return obj
            # tighten schema on retry
            ask = (
                "Return ONLY one JSON object with double-quoted keys. "
                'Schema: {"status":"ISSUE|OK|REVIEW","reasoning":"...",'
                '"risk_factors":[],"regions":[],"regulations":[],"mitigations":[]}.\n\n'
                + prompt
            )
            time.sleep(0.05)
        return None

    @staticmethod
    def cooc(text: str, *patterns: str) -> bool:
        """True if ALL patterns occur (case-insensitive) anywhere in text."""
        return all(re.search(p, text, flags=re.I) for p in patterns)