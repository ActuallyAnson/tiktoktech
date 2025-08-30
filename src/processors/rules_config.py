import re
from typing import Dict, List

# ───────────────────────────────────────────────────────────────────────────────
# Region hints by law/authority/acronym
# (Used by prescan via LAW_TO_REGIONS + LAW_PATTERNS)
# ───────────────────────────────────────────────────────────────────────────────
LAW_TO_REGIONS: Dict[str, List[str]] = {
    # US (state/federal)
    "NCMEC": ["US-Federal"],
    "COPPA": ["US-Federal"],
    "DMCA": ["US-Federal"],
    "BIPA": ["US-IL"],
    "SB976": ["US-CA"],          # CA social media for minors
    "CPRA": ["US-CA"],
    "HB 3": ["US-FL"],           # FL minor protections
    # EU / UK
    "GDPR": ["EU"],
    "DSA":  ["EU"],
    "DMA":  ["EU"],
    "EU Copyright Directive": ["EU"],
    # APAC / Americas
    "PDPA": ["SG"],              # Singapore (PDPA-SG)
    "LGPD": ["BR"],              # Brazil
    "PIPEDA": ["CA"],            # Canada
}

# ───────────────────────────────────────────────────────────────────────────────
# Domain taxonomy (align with your router/agents)
# ───────────────────────────────────────────────────────────────────────────────
DOMAINS = [
    "Child Safety",
    "Privacy & Data Protection",
    "Copyright / IP",
    "Advertising & Consumer Protection",
    "Elections & Political Ads",
    "Financial / Payments / KYC",
    "Biometrics",
    "Location / Geofencing",
    "Content Moderation / Illegal Content",
    "Accessibility",
]

# Convenience helpers
def _re(words: List[str], flags=re.I) -> List[re.Pattern]:
    """Compile a list of whole/phrase patterns."""
    return [re.compile(w, flags) for w in words]

# ───────────────────────────────────────────────────────────────────────────────
# Law/authority patterns (deterministic “hard” hits)
# If any match, prescan.required_hint = True
# ───────────────────────────────────────────────────────────────────────────────
LAW_PATTERNS: Dict[str, List[re.Pattern]] = {
    # EU / US examples with common aliases/synonyms
    "GDPR": _re([
        r"\bGDPR\b",
        r"\bGeneral\s+Data\s+Protection\s+Regulation\b",
        r"\bEU\s*GDPR\b",
    ]),
    "DSA": _re([
        r"\bDSA\b",
        r"\bDigital\s+Services\s+Act\b",
        r"\bEU\s*DSA\b",
        r"\bVLOP(s)?\b",  # very large online platforms → DSA context
    ]),
    "DMA": _re([
        r"\bDMA\b",
        r"\bDigital\s+Markets\s+Act\b",
    ]),
    "NCMEC": _re([
        r"\bNCMEC\b",
        r"\bNational\s+Center\s+for\s+Missing\s+(&|and)\s+Exploited\s+Children\b",
    ]),
    "COPPA": _re([
        r"\bCOPPA\b",
        r"\bChildren'?s\s+Online\s+Privacy\s+Protection\s+Act\b",
        r"\bunder\s*13\b",  # US federal child-privacy trigger (strong hint)
    ]),
    "CPRA": _re([
        r"\bCPRA\b",
        r"\bCalifornia\s+Privacy\s+Rights\s+Act\b",
        r"\bCCPA\b",
        r"\bCalifornia\s+Consumer\s+Privacy\s+Act\b",
        r"\bDo\s+Not\s+(Sell|Share)\b",
    ]),
    "BIPA": _re([
        r"\bBIPA\b",
        r"\bBiometric\s+Information\s+Privacy\s+Act\b",
    ]),
    "HB 3": _re([
        r"\bHB\s*3\b",
        r"\bFlorida\b.*\b(minor|child|under\s*18|social\s*media)\b",
        r"\bOnline\s+Protections\s+for\s+Minors\b",
    ]),
    "SB976": _re([
        r"\bSB\s*976\b",
        r"\bProtecting\s+Our\s+Kids\s+from\s+Social\s+Media\s+Addiction\s+Act\b",
    ]),
    "PDPA": _re([
        r"\bPDPA\b",
        r"\bPersonal\s+Data\s+Protection\s+Act\b",
        r"\bPDPA-?SG\b",
    ]),
    "LGPD": _re([
        r"\bLGPD\b",
        r"\bLei\s+Geral\s+de\s+Prote[cç][aã]o\s+de\s+Dados\b",
    ]),
    "PIPEDA": _re([
        r"\bPIPEDA\b",
        r"\bPersonal\s+Information\s+Protection\s+and\s+Electronic\s+Documents\s+Act\b",
    ]),
    "DMCA": _re([
        r"\bDMCA\b",
        r"\bDigital\s+Millennium\s+Copyright\s+Act\b",
    ]),
    "EU Copyright Directive": _re([
        r"\bEU\s+Copyright\s+Directive\b",
        r"\bDirective\s*\(EU\)\s*2019/790\b",    # DSM Article 17
        r"\bArticle\s*17\b.*\b(Directive|EU)\b",
    ]),
}

# ───────────────────────────────────────────────────────────────────────────────
# Domain keyword patterns (broader “soft” hints)
# These fire even when a law name isn’t present.
# ───────────────────────────────────────────────────────────────────────────────
DOMAIN_PATTERNS: Dict[str, List[re.Pattern]] = {
    "Child Safety": _re([
        r"\b(minor|under\s*1[38]|u1[38]|youth|child|teen|kids?)\b",
        r"\bage[-\s]*(gate|verification|check|limit|restriction|sensitive)\b",
        r"\bcurfew\b|\bbedtime\b",
        r"\bparent(al)?\s*(consent|control|notification|alert)\b",
        r"\bguardian(s)?\b|\bfamily\s*link\b",
        r"\brestricted\s*mode\b|\bvisibility\s*lock\b",
    ]),
    "Privacy & Data Protection": _re([
        r"\bconsent\b|\bopt-?out\b|\bopt-?in\b",
        r"\b(default|forced)\s*(private|public)\b",
        r"\bpersonalization\s*(off|on|toggle)\b",
        r"\bvisibility\s*settings?\b",
        r"\bdata\s*(minimi[sz]ation|deletion|erasure|retention)\b",
        r"\bguest\s*mode\b",
    ]),
    "Copyright / IP": _re([
        r"\bcopyright\b|\bIP\b|\blicens(e|ing)\b|\bright(s)?\b",
        r"\bDMCA\b|\bEU\s+Copyright\s+Directive\b|\bArticle\s*17\b",
        r"\bmusic\s*(clearance|licen[cs]e|licensing)\b",
        r"\bdownload\s*blocking\b|\bcontent\s*ID\b",
    ]),
    "Advertising & Consumer Protection": _re([
        r"\bad(s|vertis(e|ing))\b|\binfluencer\b|\bpaid\s*promotion\b",
        r"\bdisclosure\b|\blad\s*label\b|\bsponsored\b|\bpaid\s*partnership\b",
        r"\bdark\s*pattern(s)?\b|\bdeceptive\b",
        r"\bminors?\s+ads?\b|\bkid-?target(ed|ing)\b",
        r"\bendorsement\s*guidelines\b|\bFTC\b",
    ]),
    "Elections & Political Ads": _re([
        r"\bpolitic(al)?\s*(ad|advertising|content)\b",
        r"\belection\b|\bcampaign\b|\bcandidate\b|\bPAC\b|\belectioneering\b",
        r"\b(imprint|disclaimer|transparency)\s*(report|label|notice)\b",
        r"\bblackout\s*period\b|\bad\s*library\b",
    ]),
    "Financial / Payments / KYC": _re([
        r"\bKYC\b|\bAML\b|\bPEP(s)?\b|\bsanction(s)?\b|\bOFAC\b",
        r"\b(in-?app|digital)\s*purchas(es|e)\b|\bpayment(s)?\b|\bmerchant\s*of\s*record\b",
        r"\bchargeback(s)?\b|\brefund(s)?\b|\bdispute(s)?\b",
        r"\bPCI\s*DSS\b|\bcard\s*holder\s*data\b",
    ]),
    "Biometrics": _re([
        r"\b(face|voice|iris|retina|fingerprint)\s*(scan|match|recognition|template)\b",
        r"\bbiometric(s)?\b|\bfaceprint(s)?\b|\bliveness\b|\bBIPA\b",
    ]),
    "Location / Geofencing": _re([
        r"\bgeo(fence|fencing|location)\b|\bGPS\b|\bIP\b\s*(based)?\s*(block|restrict|gate)\b",
        r"\bprecise\s*location\b|\bcoarse\s*location\b",
        r"\bgeographic(al)?\s*(restriction|limit|target|bloc?k)\b",
    ]),
    "Content Moderation / Illegal Content": _re([
        r"\bmoderation\b|\btakedown\b|\bremoval\b|\breport(ing)?\b",
        r"\bvisibility\s*(lock|restriction|control)\b",
        r"\bappeal\s*(flow|process)\b",
        r"\btransparency\s*(log|report|notice)\b",
    ]),
    "Accessibility": _re([
        r"\bWCAG\b|\bEN\s*301\s*549\b",
        r"\bcaption(s|ing)\b|\bsubtitles?\b|\btranscript(s)?\b",
        r"\balt\s*text\b|\bscreen\s*reader\b|\bkeyboard\s*navigat(ion|e)\b",
        r"\bcontrast\b|\bfont\s*scal(e|ing)\b|\bassistive\b",
    ]),
}

# ───────────────────────────────────────────────────────────────────────────────
# Phrases that strongly imply legal compliance intent
# ───────────────────────────────────────────────────────────────────────────────
COMPLIANCE_LANGUAGE = _re([
    r"\bto\s+comply\s+with\b",
    r"\bin\s+accordance\s+with\b",
    r"\b(required|mandated)\s+by\s+law\b",
    r"\bas\s+required\s+by\s+(law|regulation|policy|statute)\b",
    r"\bper\s+(GDPR|DSA|COPPA|CPRA|BIPA|PDPA|LGPD|PIPEDA|DMCA)\b",
    r"\blegal\s+(requirement|obligation|basis)\b",
    r"\bcompliance\s+(logic|flow|handler|rule)\b",
    r"\bgeo-?handler\b|\bbaseline\s*behavior\b",  # internal codewords often tied to region compliance
])

# Law → primary domain(s) (used to upgrade domain hints on a law hit)
LAW_TO_DOMAINS = {
    "DSA": ["Content Moderation / Illegal Content", "Privacy & Data Protection"],
    "SB976": ["Child Safety"],
    "HB 3": ["Child Safety"],
    "Utah SMRA": ["Child Safety"],      # Utah Social Media Regulation Act (alias)
    "NCMEC": ["Content Moderation / Illegal Content", "Child Safety"],
}

# Add Utah SMRA and better aliases for the 5 regs in scope
LAW_TO_REGIONS.update({
    "Utah SMRA": ["US-UT"],
})

LAW_PATTERNS.update({
    "Utah SMRA": _re([
        r"\bUtah\b.*\bSocial\s+Media\s+Regulation\s+Act\b",
        r"\bUtah\s+SMRA\b",
    ]),
    # Strengthen SB976/HB 3 aliases
    "SB976": LAW_PATTERNS["SB976"] + _re([
        r"California\s+Social\s+Media\s+Addiction\s+Act",
        r"Protecting\s+Our\s+Kids\s+Act",
    ]),
    "HB 3": LAW_PATTERNS["HB 3"] + _re([
        r"Florida\s+Online\s+Protections\s+for\s+Minors",
    ]),
})

# Child Safety soft cues: make easy-to-miss synonyms explicit
DOMAIN_PATTERNS["Child Safety"] += _re([
    r"\bage[-\s]*sensitive\b",
    r"\bteen(ager)?s?\b",
])

# Moderation domain: include escalation machinery your dataset uses
DOMAIN_PATTERNS["Content Moderation / Illegal Content"] += _re([
    r"\bNSP\b|\bRedline\b|\bsoft\s*block\b|\bsoftblock\b",
    r"\bEchoTrace\b|\btrace\b|\baudit\b",
])

# Compliance phrasing: add internal-ish words you used (e.g., “compliance routing”)
COMPLIANCE_LANGUAGE += _re([
    r"\bcompliance\s*(routing|handler|logic)\b",
    r"\brollout\s*waves?\b",  # indicates governance, often compliance-guarded rollouts
])