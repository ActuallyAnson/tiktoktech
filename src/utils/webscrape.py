import requests
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv
from cleaner import GeminiCleaner
import google.generativeai as genai
import json
import faiss
import numpy as np
from openai import OpenAI
from google.generativeai import client

class WebScraper:
    """
    A class to scrape clean text content from a webpage.
    """
    def __init__(self, headers: dict = None):
        """
        Initializes the WebScraper.

        Args:
            headers (dict, optional): A dictionary of HTTP headers. 
                                      If None, a default User-Agent is used.
        """
        if headers:
            self.headers = headers
        else:
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        self.html_content = None
        self.clean_text = None

    def _fetch_html(self, url: str) -> bool:
        """
        Internal method to fetch HTML from a URL and store it in the instance.
        Returns True on success, False on failure.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            self.html_content = response.text
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {url}: {e}")
            self.html_content = None
            return False


    

    def _extract_clean_text(self) -> str:
        """
        Internal method to extract clean text from the stored HTML content.
        """
        if not self.html_content:
            return ""
            
        soup = BeautifulSoup(self.html_content, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()

        # Find the main content area for better quality text
        main_content = soup.find('main')
        if not main_content:
            main_content = soup.find('article')
        if not main_content:
            main_content = soup.body

        # Get text and clean it up
        text = main_content.get_text(separator=' ', strip=True)
        text = re.sub(r'\s\s+', ' ', text)
        
        return text

    def scrape(self, url: str) -> str | None:
        """
        Scrapes a single URL to fetch and extract its clean text.

        Args:
            url (str): The URL of the webpage to scrape.

        Returns:
            A string containing the cleaned text, or None if scraping fails.
        """
        print(f"Scraping URL: {url}")
        if self._fetch_html(url):
            self.clean_text = self._extract_clean_text()
            return self.clean_text
        return None

    def save_to_file(self, filepath: str) -> bool:
        """
        Saves the most recently scraped clean text to a file.

        Args:
            filepath (str): The path to the file where content will be saved.

        Returns:
            True if the file was saved successfully, False otherwise.
        """
        if not self.clean_text:
            print("Error: No text has been scraped yet. Call scrape() first.")
            return False
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.clean_text)
            print(f"Full text saved to '{filepath}'")
            return True
        except IOError as e:
            print(f"Error saving file to {filepath}: {e}")
            return False
        
def load_urls_from_json(filepath: str) -> list[str]:
    """
    Load a list of URLs from a JSON file.
    JSON format must be: { "urls": [ "url1", "url2", ... ] }
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("urls", [])

def scrape_and_clean_to_json(urls: list[str], output_file: str):
    """
    Scrapes multiple Wikipedia URLs, cleans them with Gemini, and saves results as JSONL.
    Each line in the file will be one JSON object.
    """
    load_dotenv()
    my_api_key = os.getenv("GEMINI_API_KEY")
    scraper = WebScraper()
    cleaner = GeminiCleaner(my_api_key)

    results = []

    with open(output_file, "w", encoding="utf-8") as f:
        for url in urls:
            print(f"\n🔎 Processing: {url}")
            scraped_text = scraper.scrape(url)

            if not scraped_text:
                print(f"❌ Skipping {url}, could not fetch text.")
                continue

            # Extract title from the URL (last part after '/')
            title = url

            # Clean and structure with Gemini
            cleaned_json = cleaner.clean_to_json(title, scraped_text)

            # Save one JSON object per line
            f.write(json.dumps(cleaned_json, ensure_ascii=False) + "\n")

            results.append(cleaned_json)
            print(f"✅ Saved entry for {title}")

    print(f"\n📂 Finished! All results saved to {output_file}")
    save_embeddings_to_file(filepath = 'data/embeddings_gemini.json')

    return results

def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks

def embed_text_gemini(texts,EMBEDDING_MODEL="gemini-text-embedding-3-small"):
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [np.array(e.embedding, dtype=np.float32) for e in resp.data]

def save_embeddings_to_file(filepath: str) -> bool:
    my_api_key = os.getenv("GEMINI_API_KEY")
    EMBEDDING_MODEL = "gemini-text-embedding-3-small"
    LLM_MODEL = "gpt-5-mini"
    CHUNK_SIZE = 500  # approx tokens per chunk
    TOP_K = 3         # number of chunks to retrieve

    client = OpenAI(api_key="YOUR_API_KEY")

    dataset = []
    with open("data/dataset.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            dataset.append(json.loads(line))
    chunk_data = []
    for doc in dataset:
        chunks = chunk_text(doc["content"])
        for c in chunks:
            chunk_data.append({
                "title": doc["title"],
                "summary": doc["summary"],
                "content": c
            })
    all_texts = [chunk["content"] for chunk in chunk_data]
    embeddings = embed_text_gemini(all_texts)

    # --- Store embeddings in FAISS ---
    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))

    # --- Save FAISS and metadata ---
    faiss.write_index(index, "faiss_index_gemini.bin")
    import pickle
    with open("chunk_data_gemini.pkl", "wb") as f:
        pickle.dump(chunk_data, f)


# --- Main execution block to demonstrate how to use the class ---
if __name__ == "__main__":
    urls = load_urls_from_json("data/url.json")
    save_embeddings_to_file(filepath = 'data/embeddings_gemini.json')
    #scrape_and_clean_to_json(urls, "data/dataset.jsonl")