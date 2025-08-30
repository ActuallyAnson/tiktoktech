from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # safe to call once on import

@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str = os.getenv("GEMINI_MODEL")
    # guardrails
    confidence_downgrade_guard: float = 0.80  # if prescan hinted REQUIRED, LLM can't downgrade w/o >= 0.80 conf

def get_settings() -> Settings:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set. Put it in your .env")
    return Settings(gemini_api_key=key)