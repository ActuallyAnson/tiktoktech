from __future__ import annotations
import re
from .base import BaseAgent, AgentVerdict

COMPLIANCE_LANGUAGE = [
    r"\bto\s+comply\s+with\b", r"\bin\s+accordance\s+with\b",
    r"\b(required|mandated)\s+by\s+law\b",
    r"\bas\s+required\s+by\s+(law|regulation|policy|statute)\b",
    r"\blegal\s+(requirement|obligation|basis)\b",
    r"\bcompliance\s*(routing|handler|logic)\b", r"\bgeo-?handler\b",
    r"\brollout\s*waves?\b",
]
REGION_HINTS = [
    r"\bEU\b|\bEurope(an)?\b", r"\bUS\b|\bUnited\s*States\b",
    r"\bUS-CA\b|\bCalifornia\b", r"\bUS-FL\b|\bFlorida\b", r"\bUS-UT\b|\bUtah\b",
    r"\bSG\b|\bSingapore\b", r"\bBR\b|\bBrazil\b", r"\bCA\b|\bCanada\b",
    r"\bKR\b|\bKorea\b", r"\bJP\b|\bJapan\b", r"\bIN\b|\bIndia\b",
]

class GeneralComplianceAgent(BaseAgent):
    name = "GeneralComplianceAgent"
    domain = "GeneralCompliance"

    @staticmethod
    def _prompt(text: str) -> str:
        return (
            "You are a GENERAL geo-compliance reviewer.\n"
            "Decide if the feature likely requires geo-specific handling (any domain). "
            "Look for legal/compliance phrasing, regional rollouts/limitations, or regulator signals.\n"
            "Return ONLY one JSON object: "
            '{"status":"ISSUE|OK|REVIEW","reasoning":"...",'
            '"risk_factors":[],"regions":[],"regulations":[],"mitigations":[]}.\n'
            "Allowed regulation names: [DSA, SB976, HB 3, Utah SMRA, NCMEC] or [].\n"
            "Regions limited to: [\"EU\",\"US-CA\",\"US-FL\",\"US-UT\",\"US-Federal\",\"SG\",\"BR\",\"CA\"].\n\n"
            f"TEXT:\n{text[:5000]}"
        )

    def _rule_score(self, t: str) -> float:
        s = 0.0
        if any(re.search(p, t, re.I) for p in COMPLIANCE_LANGUAGE): s += 0.5
        if any(re.search(p, t, re.I) for p in REGION_HINTS): s += 0.25
        if re.search(r"\bguardrail(s)?\b|\bguideline(s)?\b|\bpolicy\b", t, re.I): s += 0.15
        return min(s, 1.0)

    def check(self, row) -> AgentVerdict:
        t = self.text(row)
        s = self._rule_score(t)

        status = "OK"; reasoning = "No explicit compliance/region triggers."
        if s >= 0.65:
            status, reasoning = "ISSUE", "Compliance phrasing and/or region signals present."
        elif s >= 0.35:
            status, reasoning = "REVIEW", "Some compliance or region cues present."

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
