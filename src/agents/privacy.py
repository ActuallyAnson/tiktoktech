# privacy.py
from __future__ import annotations
import re
from .base import BaseAgent, AgentVerdict

PRIVACY_HINTS = [
    r"\bconsent\b", r"\bopt-?in\b", r"\bopt-?out\b",
    r"\b(default|forced)\s*(private|public)\b",
    r"\bvisibility\s*settings?\b", r"\bpersonalization\s*(off|on|toggle)\b",
    r"\bdata\s*(minimi[sz]ation|deletion|erasure|retention)\b",
    r"\bguest\s*mode\b", r"\bprivacy\b",
]

class PrivacyAgent(BaseAgent):
    name = "PrivacyAgent"
    domain = "Privacy & Data Protection"

    @staticmethod
    def _prompt(text: str) -> str:
        return (
            "You are a PRIVACY compliance reviewer.\n"
            "Decide if this feature likely requires geo-specific privacy handling (consent flows, "
            "children's consent thresholds, retention/deletion, default visibility/privacy toggles).\n"
            "Return ONLY one JSON object: "
            '{"status":"ISSUE|OK|REVIEW","reasoning":"...",'
            '"risk_factors":[],"regions":[],"regulations":[],"mitigations":[]}.\n'
            "Allowed regulation names: [DSA, NCMEC, SB976, HB 3, Utah SMRA] when privacy intersects minors/moderation; else [].\n"
            "Regions limited to: [\"EU\",\"US-CA\",\"US-FL\",\"US-UT\",\"US-Federal\",\"SG\",\"BR\",\"CA\"].\n\n"
            f"TEXT:\n{text[:5000]}"
        )

    def _rule_score(self, t: str) -> float:
        s = 0.0
        bumps = [0.25,0.20,0.20,0.15,0.15,0.10,0.15,0.10,0.05]
        for rx, w in zip(PRIVACY_HINTS, bumps):
            if re.search(rx, t, re.I): s += w
        # Co-occurrence: consent + retention → stronger
        if self.cooc(t, r"\bconsent\b", r"\b(retention|deletion|erasure|minimi[sz]ation)\b"): s += 0.15
        return min(s, 1.0)

    def check(self, row) -> AgentVerdict:
        t = self.text(row)
        s = self._rule_score(t)

        status = "OK"; reasoning = "No explicit privacy triggers."
        if s >= 0.65:
            status, reasoning = "ISSUE", "Strong privacy indicators (consent/retention/visibility)."
        elif s >= 0.35:
            status, reasoning = "REVIEW", "Partial privacy indicators."

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
