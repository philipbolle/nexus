"""
NEXUS Embeddings Service
Generate embeddings locally using sentence-transformers.
Free, fast, runs on CPU.
"""

import logging
from typing import List
from functools import lru_cache

logger = logging.getLogger(__name__)

# Lazy load model to avoid startup delay
_model = None


def _get_model():
    """Load model on first use."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model (first use)...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded")
    return _model


def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for text using all-MiniLM-L6-v2.

    Returns 384-dimensional vector.
    Runs locally on CPU - FREE.
    """
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import numpy as np
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings (384 for MiniLM)."""
    return 384
