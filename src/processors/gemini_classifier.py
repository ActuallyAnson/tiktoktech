"""
Gemini classifier for geo-compliance detection.
"""

import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.generative_models import GenerativeModel
from google.generativeai.client import configure
from .prompt_templates import build_classification_prompt
from .text_preprocessor import expand_terminology

class GeminiClassifier:
    #constructor to load api key from .env
    def __init__(self) -> None:
        load_dotenv()

        my_api_key = os.getenv("GEMINI_API_KEY")
        
        # Check if API key exists
        if not my_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
        
        # Configure Gemini
        try:
            configure(api_key=my_api_key)
            
            # Store the model for later use
            self.model = GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            raise ValueError(f"Failed to configure Gemini API: {str(e)}. Check your API key and library version.")

    #expand terminology, build prompt, send to gemini, parse response from gemini to dict
    def classify_feature(self, feature_name:str, feature_description:str) -> Dict[str, Any]:
        try:
            expanded_name = expand_terminology(feature_name)
            expanded_desc = expand_terminology(feature_description)

            prompt = build_classification_prompt (expanded_name,expanded_desc)

            response = self.model.generate_content(prompt)

            # Parse the JSON response
            parsed_result = self._parse_json_response(response.text)
            
            # Add some metadata
            parsed_result["original_feature_name"] = feature_name
            parsed_result["expanded_feature_name"] = expanded_name
            
            return parsed_result

        except Exception as e:
            return {'Error!': str(e)}
    

    #parse Gemini's response to extract json
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        try:
            # remove extra whitespace
            text = response_text.strip()
            
            # Look for JSON block between ```json and ```
            if "```json" in text:
                start = text.find("```json") + 7  # Skip past "```json"
                end = text.find("```", start)    # Find closing ```
                json_text = text[start:end].strip()
            # Or look for just { ... }
            elif "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                json_text = text[start:end]
            else:
                json_text = text
            
            # Parse the JSON
            result = json.loads(json_text)
            return result
            
        except json.JSONDecodeError as e:
            return {
                "classification": "PARSE_ERROR",
                "reasoning": f"Could not parse JSON: {str(e)}",
                "confidence": 0.0,
                "related_regulations": [],
                "raw_response": response_text
            }