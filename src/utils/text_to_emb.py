# generate_embeddings.py

import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import pickle

# --- Load JSONL dataset ---
dataset = []
with open("data/dataset.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        dataset.append(json.loads(line))

# --- Chunking function ---
CHUNK_SIZE = 500
def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# --- Prepare chunks ---
chunk_data = []
for doc in dataset:
    chunks = chunk_text(doc["content"])
    for c in chunks:
        chunk_data.append({
            "title": doc["title"],
            "summary": doc["summary"],
            "content": c
        })

# --- Generate embeddings locally ---
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
all_texts = [c["content"] for c in chunk_data]
embeddings = embed_model.encode(all_texts, convert_to_numpy=True)

# --- Store embeddings in FAISS ---
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings, dtype=np.float32))

# --- Save FAISS index and metadata ---
faiss.write_index(index, "data/faiss_index_local.bin")
with open("data/chunk_data_local.pkl", "wb") as f:
    pickle.dump(chunk_data, f)

print("✅ FAISS index and chunk data saved successfully.")