"""
FAISS vector index for code embeddings with caching support.
"""

import os
from pathlib import Path
from typing import List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.rag.cache import EmbeddingCache
from src.rag.ingest import CodeChunk


class CodeIndex:
    """FAISS vector index for code embeddings with embedding cache."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_dir: str = ".rag_cache",
    ):
        """
        Initialize the code index.

        Args:
            model_name: Name of the sentence-transformers model
            cache_dir: Directory for embedding cache
        """
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_embedding_dimension()
        self.index: Optional[faiss.Index] = None
        self.chunks: List[CodeChunk] = []
        self.cache = EmbeddingCache(cache_dir)

    def build_index(self, chunks: List[CodeChunk]) -> None:
        """
        Build FAISS index from code chunks.

        Args:
            chunks: List of CodeChunk objects to index
        """
        self.chunks = list(chunks)

        # Create IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.embedding_dim)

        embeddings = []
        for chunk in chunks:
            # Check cache first
            cached_embedding = self.cache.get(chunk.code)
            if cached_embedding is not None:
                embedding = cached_embedding
            else:
                # Encode and cache
                embedding = self.model.encode(
                    chunk.code,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                self.cache.set(chunk.code, embedding)

            embeddings.append(embedding)

        # Convert to matrix and add to index
        if embeddings:
            embeddings_matrix = np.array(embeddings).astype("float32")
            self.index.add(embeddings_matrix)

    def search(self, query: str, k: int = 3) -> List[CodeChunk]:
        """
        Search for similar code chunks.

        Args:
            query: Search query string
            k: Number of results to return

        Returns:
            List of top-k most similar CodeChunks
        """
        if self.index is None or len(self.chunks) == 0:
            return []

        # Encode query with normalization
        query_embedding = (
            self.model.encode(
                query,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            .reshape(1, -1)
            .astype("float32")
        )

        # Search index
        k = min(k, len(self.chunks))
        distances, indices = self.index.search(query_embedding, k)

        # Return corresponding chunks
        results = []
        for idx in indices[0]:
            if idx >= 0 and idx < len(self.chunks):
                results.append(self.chunks[idx])

        return results

    def save_index(self, path: str) -> None:
        """
        Save the FAISS index and chunks to disk.

        Args:
            path: Path to save the index files
        """
        if self.index is None:
            raise ValueError("No index to save")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(path.with_suffix(".index")))

        # Save chunks metadata
        chunks_data = [
            {
                "code": chunk.code,
                "metadata": chunk.metadata,
                "chunk_type": chunk.chunk_type,
                "file_path": chunk.file_path,
            }
            for chunk in self.chunks
        ]
        with open(path.with_suffix(".chunks.pkl"), "wb") as f:
            import pickle

            pickle.dump(chunks_data, f)

        # Save cache
        cache_path = path.parent / ".rag_cache"
        if cache_path.exists():
            import shutil

            shutil.copytree(cache_path, path.with_suffix(".cache"), dirs_exist_ok=True)

    def load_index(self, path: str) -> None:
        """
        Load the FAISS index and chunks from disk.

        Args:
            path: Path to load the index files from
        """
        path = Path(path)

        # Load FAISS index
        self.index = faiss.read_index(str(path.with_suffix(".index")))

        # Load chunks
        with open(path.with_suffix(".chunks.pkl"), "rb") as f:
            import pickle

            chunks_data = pickle.load(f)

        self.chunks = [
            CodeChunk(
                code=data["code"],
                metadata=data["metadata"],
                chunk_type=data["chunk_type"],
                file_path=data["file_path"],
            )
            for data in chunks_data
        ]

        # Load cache
        cache_path = path.with_suffix(".cache")
        if cache_path.exists():
            import shutil

            self.cache = EmbeddingCache(str(cache_path))
