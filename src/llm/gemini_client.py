from __future__ import annotations
from typing import Optional
from google.generativeai.generative_models import GenerativeModel
from google.generativeai.client import configure

class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        configure(api_key=api_key)
        self.model = GenerativeModel(model_name)

    def generate(self, prompt: str, safety_settings: Optional[dict] = None) -> str:
        """Return raw text from Gemini; caller handles parsing."""
        resp = self.model.generate_content(
            contents=prompt,
            generation_config={
                "temperature": 0,
                "top_p": 1,
                "response_mime_type": "application/json"
            }
        )
        return resp.text