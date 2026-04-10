"""
Embedding cache for avoiding recomputation of repeated code embeddings.
"""

import hashlib
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np


class EmbeddingCache:
    """File-based cache for code embeddings using SHA-256 hash as key."""

    def __init__(self, cache_dir: str = ".rag_cache"):
        """
        Initialize the embedding cache.

        Args:
            cache_dir: Directory to store cached embeddings
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, text: str) -> str:
        """Generate SHA-256 hash of text for cache key."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.pkl"

    def get(self, text: str) -> Optional[np.ndarray]:
        """
        Retrieve cached embedding for text.

        Args:
            text: The code text to look up

        Returns:
            Cached embedding as numpy array, or None if not cached
        """
        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)

        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    return pickle.load(f)
            except (pickle.PickleError, IOError):
                # Invalid cache file, remove and return None
                cache_path.unlink(missing_ok=True)

        return None

    def set(self, text: str, embedding: np.ndarray) -> None:
        """
        Store embedding in cache.

        Args:
            text: The code text
            embedding: The embedding to cache
        """
        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(embedding, f)
        except (pickle.PickleError, IOError):
            # Failed to write cache, ignore
            pass

    def clear(self) -> None:
        """Clear all cached embeddings."""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink(missing_ok=True)

    def __len__(self) -> int:
        """Return number of cached embeddings."""
        return len(list(self.cache_dir.glob("*.pkl")))

    def has(self, text: str) -> bool:
        """Check if text has a cached embedding."""
        cache_key = self._get_cache_key(text)
        return self._get_cache_path(cache_key).exists()
