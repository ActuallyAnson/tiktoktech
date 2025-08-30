import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
import plotly.express as px
import plotly.io as pio
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

def view_embeddings_3d(query=None, top_k=3):
    
    pio.renderers.default = "browser"

    # --- Load FAISS index and chunk metadata ---
    index = faiss.read_index("data/faiss_index_local.bin")
    with open("data/chunk_data_local.pkl", "rb") as f:
        chunk_data = pickle.load(f)

    n_vectors = index.ntotal
    all_embeddings = index.reconstruct_n(0, n_vectors)

    # Default plot
    plot_embeddings = all_embeddings
    plot_labels = [c['title'] for c in chunk_data]
    marker_sizes = [5] * len(all_embeddings)  # default size

    # --- If query provided ---
    if query:
        query_embedding = embed_model.encode([query], convert_to_numpy=True).reshape(1, -1)
        distances, indices = index.search(query_embedding, top_k)
        nearest_indices = [int(i) for i in indices[0]]

        # Add query as the last point
        plot_embeddings = np.vstack([all_embeddings, query_embedding])
        plot_labels.append("User Query")
        marker_sizes.append(12)  # Query point largest

        # Increase size of nearest neighbors
        for idx in nearest_indices:
            marker_sizes[idx] = 9

    # --- PCA to 3D ---
    pca = PCA(n_components=3)
    embeddings_3d = pca.fit_transform(plot_embeddings)

    # --- Create Plotly 3D scatter ---
    fig = px.scatter_3d(
        x=embeddings_3d[:,0],
        y=embeddings_3d[:,1],
        z=embeddings_3d[:,2],
        color=plot_labels,       # keep original colors
        opacity=0.7,
        title=f"FAISS Embeddings (Query: '{query}' Top {top_k})" if query else "Global FAISS Embeddings"
    )

    # --- Assign marker sizes correctly ---
    for trace in fig.data:
        trace.marker.size = [marker_sizes[i] for i, lbl in enumerate(plot_labels) if lbl == trace.name]

    fig.show()



if __name__ == "__main__":
    view_embeddings_3d()  # View all