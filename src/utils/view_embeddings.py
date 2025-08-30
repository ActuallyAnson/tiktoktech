import faiss
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.decomposition import PCA
import plotly.express as px
import plotly.io as pio

# Load embedding model once
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

def view_embeddings_3d(query=None, top_k=3):
    pio.renderers.default = "browser"

    # === Load FAISS index and chunk metadata ===
    index = faiss.read_index("data/faiss_index_local.bin")
    with open("data/chunk_data_local.pkl", "rb") as f:
        chunk_data = pickle.load(f)

    n_vectors = index.ntotal
    embeddings = index.reconstruct_n(0, n_vectors)

    # By default, plot all embeddings
    plot_embeddings = embeddings
    plot_chunks = chunk_data
    plot_titles = [c['title'] for c in plot_chunks]
    labels = [f"Title: {c['title']}<br>Summary: {c['summary'][:150]}..." for c in plot_chunks]

    # --- If query is provided, retrieve top-k nearest ---
    if query:
        query_embedding = embed_model.encode([query], convert_to_numpy=True).reshape(1, -1)
        distances, indices = index.search(query_embedding, top_k)
        top_embeddings = np.array([embeddings[i] for i in indices[0]])
        top_chunks = [chunk_data[i] for i in indices[0]]

        # Add the query embedding as a separate point
        plot_embeddings = np.vstack([top_embeddings, query_embedding])
        plot_chunks = top_chunks + [{"title": "User Query", "summary": query}]

        labels = [
            f"Title: {c['title']}<br>Summary: {c['summary'][:150]}..." for c in plot_chunks
        ]
        plot_titles = [c['title'] for c in plot_chunks]

    # === PCA to 3D ===
    pca = PCA(n_components=3)
    embeddings_3d = pca.fit_transform(plot_embeddings)

    # === Interactive 3D Plot with color by title ===
    fig = px.scatter_3d(
        x=embeddings_3d[:,0],
        y=embeddings_3d[:,1],
        z=embeddings_3d[:,2],
        color=plot_titles,
        
        opacity=0.7,
        title=f"FAISS Embeddings in 3D {'(Top-'+str(top_k)+' for Query)' if query else ''}"
    )

    fig.update_traces(marker=dict(size=5), textposition="top center")
    fig.show()

view_embeddings_3d()  # View all