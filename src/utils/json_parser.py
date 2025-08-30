from __future__ import annotations
import json

def strict_json_array(text: str):
    s = (text or "").strip()
    if "```json" in s:
        i = s.find("```json") + 7
        j = s.find("```", i)
        s = s[i:j].strip()
    elif "[" in s and "]" in s:
        s = s[s.find("["): s.rfind("]") + 1]
    return json.loads(s)