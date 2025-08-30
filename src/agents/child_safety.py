from __future__ import annotations
import re
from .base import BaseAgent, AgentVerdict

CHILD_TERMS = r"\b(minor|teen|teenager(s)?|child|kids?|underage|youth)\b"
AGE_CTRL    = r"\bage[-\s]*(gate|verification|check|limit|restriction|sensitive)\b"
MOD_SIGNALS = r"\bmoderation|moderate|review(ing)?|flag(ged|ging)?|stricter\b"

class ChildSafetyAgent(BaseAgent):
    name = "ChildSafetyAgent"
    domain = "Child Safety"

    @staticmethod
    def _prompt(text: str) -> str:
        return (
            "You are a CHILD-SAFETY compliance reviewer for social-media features.\n"
            "Goal: decide if the feature implicates minor protections requiring geo-specific compliance "
            "(e.g., age gating, parental consent, youth curfews, teen visibility limits).\n"
            "Return ONLY one JSON object with keys: "
            '{"status":"ISSUE|OK|REVIEW","reasoning":"...",'
            '"risk_factors":[],"regions":[],"regulations":[],"mitigations":[]}.\n'
            "Rules:\n"
            "- Consider only these regulation names if applicable: [SB976, HB 3, Utah SMRA, DSA, NCMEC]. If none, use [].\n"
            "- Regions must be chosen from: [\"EU\",\"US-CA\",\"US-FL\",\"US-UT\",\"US-Federal\",\"SG\",\"BR\",\"CA\"]. If unknown, use [].\n"
            "- Prefer ISSUE when minors + explicit age controls or parental requirements are present.\n\n"
            f"TEXT:\n{text[:5000]}"
        )

    def check(self, row) -> AgentVerdict:
        t = self.text(row)

        s = 0.0
        if self.has(CHILD_TERMS, t): s += 0.30
        if self.has(AGE_CTRL, t):    s += 0.30
        if self.cooc(t, CHILD_TERMS, AGE_CTRL): s += 0.20
        if self.cooc(t, CHILD_TERMS, MOD_SIGNALS): s += 0.25
        if self.cooc(t, CHILD_TERMS, r"\bpolicy\s*(framework)?\b"): s += 0.10
        s = min(s, 1.0)

        status = "OK"
        reasoning = "No explicit minors/age-control cues."
        if s >= 0.65:
            status, reasoning = "ISSUE", "Strong minors + age-control indicators."
        elif s >= 0.35:
            status, reasoning = "REVIEW", "Partial minors indicators."

        if self.llm and self.llm_enabled and (self.llm_mode == "always" or status == "REVIEW"):
            obj = self.llm_json(self._prompt(t),
                                expect_keys=("status","reasoning"))
            if obj and obj.get("status") in {"ISSUE","OK","REVIEW"}:
                status = obj["status"]
                extra = []
                if obj.get("risk_factors"):  extra.append("risk=" + ", ".join(obj["risk_factors"][:3]))
                if obj.get("regions"):       extra.append("regions=" + ", ".join(obj["regions"][:4]))
                if obj.get("regulations"):   extra.append("regs=" + ", ".join(obj["regulations"]))
                if obj.get("mitigations"):   extra.append("mitigations=" + "; ".join(obj["mitigations"][:2]))
                if extra:
                    reasoning = f"{reasoning} | LLM: {obj.get('reasoning','').strip()} | " + " | ".join(extra)
                else:
                    reasoning = f"{reasoning} | LLM: {obj.get('reasoning','').strip()}"

                s = {"ISSUE": 0.9, "REVIEW": 0.6, "OK": max(s, 0.5)}[status]

        return AgentVerdict(agent=self.name, status=status, score=round(s, 2), reasoning=reasoning)
