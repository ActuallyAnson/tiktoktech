# get_context_chunk.py

import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# --- Load FAISS index and chunk data ---
index = faiss.read_index("data/faiss_index_local.bin")
with open("data/chunk_data_local.pkl", "rb") as f:
    chunk_data = pickle.load(f)

# --- Load embedding model ---
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

TOP_K = 3

def get_context(user_question, top_k=3):
    # Embed the user query locally
    query_embedding = embed_model.encode([user_question], convert_to_numpy=True).reshape(1, -1)
    
    # Retrieve top-k chunks
    distances, indices = index.search(query_embedding, top_k)
    retrieved_chunks = [chunk_data[i] for i in indices[0]]
    
    # Print titles of retrieved chunks
    titles = list({c['title'] for c in retrieved_chunks})  # unique titles
    print("✅ Retrieved Context Titles:")
    for t in titles:
        print("-", t)


    # Build context text
    context_text = "\n\n".join([
        f"Title: {c['title']}\nSummary: {c['summary']}\nContent: {c['content']}"
        for c in retrieved_chunks
    ])
    
    return context_text

# --- Example usage ---
if __name__ == "__main__":
    question = "What are the key obligations of the Digital Services Act?"
    context = get_context(question)
    print("--- Retrieved Context ---\n")
    print(context[:1000] + "...\n")  # preview first 1000 chars