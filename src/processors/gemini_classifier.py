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
from utils.get_context import get_context

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
            self.model = GenerativeModel("gemini-2.5-flash")
        except Exception as e:
            raise ValueError(f"Failed to configure Gemini API: {str(e)}. Check your API key and library version.")

    #expand terminology, build prompt, send to gemini, parse response from gemini to dict
    def classify_feature(self, feature_name:str, feature_description:str) -> Dict[str, Any]:
        try:
            expanded_name = expand_terminology(feature_name)
            expanded_desc = expand_terminology(feature_description)

            context = get_context(expanded_desc)
            self.context = f"""
You are an expert assistant. Answer the question **solely based on the context below**. 
Do NOT use external information, your training data, or any web search. 
If the answer is not present in the context,give your confident score as 0'.

Context:
{context}

"""
            with open("data/context.txt", 'w', encoding='utf-8') as f:
                json.dump({'context': self.context}, f, ensure_ascii=False, indent=2)

            prompt = build_classification_prompt (expanded_name,expanded_desc,self.context)

            response = self.model.generate_content(prompt)

            # Parse the JSON response
            parsed_result = self._parse_json_response(response.text)
            
            # Add some metadata
            parsed_result["original_feature_name"] = feature_name
            parsed_result["expanded_feature_name"] = expanded_name
            
            return parsed_result

        except Exception as e:
            return {'Error!': str(e)}
    
    def classify_features_batch(self, features_batch: list, batch_size: int = 5) -> list:
        """
        Classify multiple features in a single API call for efficiency.
        
        Args:
            features_batch: List of dicts with 'feature_name' and 'feature_description'
            batch_size: Number of features to process in one API call
        
        Returns:
            List of classification results
        """
        try:
            # Prepare the batch data with expanded terminology
            batch_data = []
            for i, feature in enumerate(features_batch):
                expanded_name = expand_terminology(feature['feature_name'])
                expanded_desc = expand_terminology(feature['feature_description'])
                batch_data.append({
                    'index': i,
                    'feature_name': feature['feature_name'],
                    'expanded_name': expanded_name,
                    'expanded_desc': expanded_desc
                })
            
            # Build batch prompt
            batch_prompt = self._build_batch_prompt(batch_data)
            
            # Make single API call
            response = self.model.generate_content(batch_prompt)
            
            # Parse batch response
            batch_results = self._parse_batch_response(response.text, batch_data)
            
            return batch_results
            
        except Exception as e:
            # Return error for all features in batch
            return [{'Error!': str(e)} for _ in features_batch]
    
    def _build_batch_prompt(self, batch_data: list) -> str:
        """Build a prompt for multiple features at once."""
        prompt = """You are an expert in geo-regulation compliance for social media platforms. Analyze the following TikTok features and classify each one.

For EACH feature, determine if it requires geo-specific compliance logic by checking if it implements region-specific laws like:
- EU Digital Services Act (DSA)
- California SB976 (social media age requirements)
- Florida HB 3 (social media restrictions for minors)
- Utah Social Media Regulation Act
- US NCMEC reporting requirements for child safety content

Respond with a JSON array where each object has this structure:
{
  "feature_index": <number>,
  "classification": "REQUIRED" | "NOT REQUIRED" | "NEEDS HUMAN REVIEW",
  "reasoning": "<detailed explanation>",
  "confidence": <float 0.0-1.0>,
  "related_regulations": [<list of applicable laws>]
}

IMPORTANT: Use 0-based indexing for feature_index (first feature = 0, second feature = 1, etc.)

Features to analyze:

"""
        
        for item in batch_data:
            prompt += f"""
Feature {item['index']}:
Name: {item['expanded_name']}
Description: {item['expanded_desc']}

"""
        
        prompt += """
Return ONLY the JSON array with classifications for all features. No additional text."""
        
        return prompt
    
    def _parse_batch_response(self, response_text: str, batch_data: list) -> list:
        """Parse the batch JSON response."""
        try:
            # Clean the response
            text = response_text.strip()
            
            # Extract JSON array
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                json_text = text[start:end].strip()
            elif "[" in text and "]" in text:
                start = text.find("[")
                end = text.rfind("]") + 1
                json_text = text[start:end]
            else:
                raise ValueError("No JSON array found in response")
            
            import json
            results_array = json.loads(json_text)
            
            # Map results back to original features
            final_results = []
            for item in batch_data:
                feature_index = item['index']
                
                # Find the result for this feature
                feature_result = None
                for result in results_array:
                    if result.get('feature_index') == feature_index:
                        feature_result = result
                        break
                
                if feature_result:
                    final_results.append({
                        'classification': feature_result.get('classification', 'NEEDS HUMAN REVIEW'),
                        'reasoning': feature_result.get('reasoning', 'No reasoning provided'),
                        'confidence': feature_result.get('confidence', 0.5),
                        'related_regulations': feature_result.get('related_regulations', []),
                        'original_feature_name': item['feature_name'],
                        'expanded_feature_name': item['expanded_name']
                    })
                else:
                    # Fallback if result not found
                    final_results.append({
                        'classification': 'NEEDS HUMAN REVIEW',
                        'reasoning': 'Result not found in batch response',
                        'confidence': 0.0,
                        'related_regulations': [],
                        'original_feature_name': item['feature_name'],
                        'expanded_feature_name': item['expanded_name']
                    })
            
            return final_results
            
        except Exception as e:
            # Return fallback results
            return [{
                'classification': 'ERROR',
                'reasoning': f'Batch parsing error: {str(e)}',
                'confidence': 0.0,
                'related_regulations': [],
                'original_feature_name': item['feature_name'],
                'expanded_feature_name': item['expanded_name']
            } for item in batch_data]
    

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