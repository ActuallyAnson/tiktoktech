"""
Text preprocessor for expanding TikTok internal terminology.
Converts abbreviations to full terms for better LLM understanding.
Anson
"""

import json
import re #regular expression
from pathlib import Path
from typing import Dict, Optional

def load_terminology() -> Dict[str, str]:
    terminology_path = Path(__file__).parent.parent.parent / "data" / "terminology.json"

    with open(terminology_path, 'r') as f:
        return json.load(f)
    
def expand_terminology(text: str, terminology: Optional[Dict[str,str]] = None) -> str:
    if terminology is None:
        terminology = load_terminology() 

    expanded_text = text
    for abbrev, full_term in terminology.items():
        expanded_text = re.sub(r'\b' + re.escape(abbrev) + r'\b', full_term, expanded_text)
    
    return expanded_text