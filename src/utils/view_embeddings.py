import faiss
import pickle
import numpy as np
from sklearn.decomposition import PCA
import plotly.express as px
import plotly.io as pio

pio.renderers.default = "browser"

# === Load FAISS index and chunk metadata ===
index = faiss.read_index("data/faiss_index_local.bin")
with open("data/chunk_data_local.pkl", "rb") as f:
    chunk_data = pickle.load(f)

n_vectors = index.ntotal
embeddings = index.reconstruct_n(0, n_vectors)



# === Use titles for color grouping ===
titles = [c['title'] for c in chunk_data]

# === PCA to 3D ===
pca = PCA(n_components=3)
embeddings_3d = pca.fit_transform(embeddings)

# === Interactive 3D Plot with color by title ===
fig = px.scatter_3d(
    x=embeddings_3d[:,0],
    y=embeddings_3d[:,1],
    z=embeddings_3d[:,2],
    color=titles,      # 👈 color points by title
    opacity=0.7,
    title="FAISS Embeddings in 3D (Grouped by Title)",
)

fig.update_traces(marker=dict(size=5), textposition="top center")
fig.show()
