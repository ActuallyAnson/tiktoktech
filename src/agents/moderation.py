# moderation.py
from __future__ import annotations
import re
from .base import BaseAgent, AgentVerdict

MOD_HINTS = [
    r"\bmoderation\b",
    r"\btake\s*down\b|\btakedown\b|\bremoval\b",
    r"\breport(ing)?\b",
    r"\bappeal\s*(flow|process)\b",
    r"\btransparency\s*(log|report|notice)\b",
    r"\bvisibility\s*(lock|restriction|control)\b|\brestricted\s*mode\b",
    r"\bNSP\b|\bRedline\b|\bsoft\s*block\b|\bsoftblock\b",
    r"\bEchoTrace\b|\btrace\b|\baudit\b",
]

CHILD_TERMS = r"\b(minor|teen|teenager(s)?|child|kids?|underage|youth)\b"

class ModerationAgent(BaseAgent):
    name = "ModerationAgent"
    domain = "Content Moderation / Illegal Content"

    @staticmethod
    def _prompt(text: str) -> str:
        return (
            "You are a CONTENT-MODERATION compliance reviewer.\n"
            "Decide if the feature triggers geo-specific duties (e.g., EU DSA transparency, notice, appeals; "
            "illegal-content routing; account restrictions; visibility limits).\n"
            "Return ONLY one JSON object: "
            '{"status":"ISSUE|OK|REVIEW","reasoning":"...",'
            '"risk_factors":[],"regions":[],"regulations":[],"mitigations":[]}.\n'
            "Use only these regulation names if relevant: [DSA, NCMEC]. Others → [].\n"
            "Regions from: [\"EU\",\"US-Federal\",\"US-CA\",\"US-FL\",\"US-UT\",\"SG\",\"BR\",\"CA\"]. Unknown → [].\n\n"
            f"TEXT:\n{text[:5000]}"
        )

    def _rule_score(self, t: str) -> float:
        s = 0.0
        weights = [0.25,0.20,0.15,0.15,0.15,0.10,0.10,0.05]
        for rx, w in zip(MOD_HINTS, weights):
            if re.search(rx, t, re.I): s += w
        # Co-occurrence bumps: notice+appeal, transparency+reporting
        if self.cooc(t, r"\bnotice\b", r"\bappeal"): s += 0.15
        if self.cooc(t, r"\btransparency\b", r"\breport"): s += 0.10
        if self.cooc(t, CHILD_TERMS, r"\bmoderation|moderate|stricter\b"): s += 0.20
        return min(s, 1.0)

    def check(self, row) -> AgentVerdict:
        t = self.text(row)
        s = self._rule_score(t)

        status = "OK"; reasoning = "No explicit moderation/transparency triggers."
        if s >= 0.65:
            status, reasoning = "ISSUE", "Strong moderation/transparency indicators."
        elif s >= 0.35:
            status, reasoning = "REVIEW", "Partial moderation indicators."

        if self.llm and self.llm_enabled and (self.llm_mode == "always" or status == "REVIEW"):
            obj = self.llm_json(self._prompt(t))
            if obj and obj.get("status") in {"ISSUE","OK","REVIEW"}:
                status = obj["status"]
                extra = []
                if obj.get("risk_factors"):  extra.append("risk=" + ", ".join(obj["risk_factors"][:3]))
                if obj.get("regions"):       extra.append("regions=" + ", ".join(obj["regions"][:4]))
                if obj.get("regulations"):   extra.append("regs=" + ", ".join(obj["regulations"]))
                if obj.get("mitigations"):   extra.append("mitigations=" + "; ".join(obj["mitigations"][:2]))
                reasoning = f"{reasoning} | LLM: {obj.get('reasoning','').strip()}" + ((" | " + " | ".join(extra)) if extra else "")
                s = {"ISSUE": 0.9, "REVIEW": 0.6, "OK": max(s, 0.5)}[status]

        return AgentVerdict(agent=self.name, status=status, score=round(s, 2), reasoning=reasoning)
