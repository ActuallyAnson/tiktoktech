import faiss
import pickle
import numpy as np
import plotly.express as px
import plotly.io as pio
from sklearn.decomposition import PCA
from sentence_transformers import SentenceTransformer
import os # To help with shortening URLs for labels

# Dummy embed_model for demonstration if not defined elsewhere
try:
    embed_model
except NameError:
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Dummy SentenceTransformer loaded for demonstration. Ensure your actual embed_model is loaded.")

def view_embeddings_3d(query=None, top_k=2):
    try:
        pio.renderers.default = "browser"

        # === Load FAISS index and chunk metadata ===
        index = faiss.read_index("data/faiss_index_local.bin")
        with open("data/chunk_data_local.pkl", "rb") as f:
            chunk_data = pickle.load(f)

        n_vectors = index.ntotal
        all_embeddings = index.reconstruct_n(0, n_vectors)

        plot_embeddings = all_embeddings
        
        # --- Create clean labels for the plot legend ---
        # Long URLs in the legend are messy. Let's shorten them.
        def get_label(chunk):
            title = chunk['title']
            if title.startswith('http'):
               
                return title
            return title

        # This list of labels will be used for coloring and the legend
        plot_labels = [get_label(c) for c in chunk_data]
        
        # --- If query is provided, find neighbors and modify labels/embeddings ---
        if query:
            query_embedding = embed_model.encode([query], convert_to_numpy=True).reshape(1, -1)
            plot_embeddings = np.vstack([all_embeddings, query_embedding])
            
            distances, indices = index.search(query_embedding, top_k)
            nearest_indices = indices[0]
            
            # Modify the labels for the nearest neighbors
            for i in nearest_indices:
                plot_labels[i] = "Nearest Neighbor"
            
            # Add the query's label
            plot_labels.append("User Query")
            
        # === PCA to 3D ===
        pca = PCA(n_components=3)
        embeddings_3d = pca.fit_transform(plot_embeddings)

        # === Interactive 3D Plot ===
        # Map our special labels to specific colors
        color_map = {
            "Nearest Neighbor": "black",
            "User Query": "red"
        }

        fig = px.scatter_3d(
            x=embeddings_3d[:,0],
            y=embeddings_3d[:,1],
            z=embeddings_3d[:,2],
            color=plot_labels,       # Use the clean labels for coloring
            color_discrete_map=color_map, # Apply our specific color map
            opacity=0.7,
            title=f"FAISS Embeddings (Query: '{query}' with Top {top_k} Neighbors)" if query else "Global View of FAISS Embeddings"
        )

        # --- Update marker sizes AFTER plot creation ---
        if query:
            # Create a list of sizes for all points
            marker_sizes = [5] * len(all_embeddings) # Default size
            
            # Increase size for nearest neighbors
            for idx in nearest_indices:
                marker_sizes[idx] = 8
            
            # Largest size for the query point (which is the last one)
            marker_sizes.append(10)
            

            fig.update_traces(marker=dict(size=marker_sizes))
        else:
            fig.update_traces(marker=dict(size=5))

        fig.show()

    except Exception as e:
        print(f" Error in view_embeddings_3d: {e}")


if __name__ == "__main__":
    view_embeddings_3d()  # View all