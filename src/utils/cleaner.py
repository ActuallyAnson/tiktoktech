import google.generativeai as genai
import os
from dotenv import load_dotenv




import google.generativeai as genai
import json

class GeminiCleaner:
    """
    A class to clean scraped text using Google's Gemini API and return structured JSON.
    """
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def clean_to_json(self, title: str, scraped_text: str) -> dict:
        """
        Sends scraped text to Gemini and returns structured JSON.
        """
        prompt = f"""
        You are a text cleaner. I will give you raw text scraped from a website.
        Your job: clean it and output in valid JSON format only.

        Rules:
        - Remove references like [1], [2], [citation needed].
        - Remove headings like 'See also', 'References', 'External links'.
        - Remove HTML/Markdown tags.
        - Keep only clean, plain sentences.
        - Do not add explanations outside of JSON.

        JSON format:
        {{
          "title": "{title}",
          "summary": "first paragraph only",
          "content": "cleaned full article text"
        }}

        Here is the text:
        {scraped_text}
        """

        response = self.model.generate_content(prompt)
        cleaned_json = response.text.strip()

            # 🔹 Remove Markdown code fences if present
        if cleaned_json.startswith("```"):
            cleaned_json = cleaned_json.strip("`")  # remove backticks
            # Sometimes Gemini prepends 'json\n'
            cleaned_json = cleaned_json.replace("json\n", "", 1).replace("json", "", 1)
            # Try parsing JSON, fall back to raw text if needed

        try:
            return json.loads(cleaned_json)
        except json.JSONDecodeError:
            print("⚠️ Warning: Gemini did not return valid JSON, returning raw text instead.")
            return {"title": title, "summary": "", "content": cleaned_json}