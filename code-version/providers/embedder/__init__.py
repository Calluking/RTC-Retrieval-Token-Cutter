"""Embedder providers for text embedding."""

from core.interfaces import Embedder
from .mock_embedder import ZeroEmbedder, MOCK_EMBEDDING_DIM

def get_openai_embedder():
    """Lazy-load OpenAIEmbedder. Requires: pip install openai"""
    from .openai_embedder import OpenAIEmbedder, CachedOpenAIEmbedder
    return OpenAIEmbedder, CachedOpenAIEmbedder

__all__ = [
    "Embedder",
    # Utility/test implementations
    "ZeroEmbedder",
    "MOCK_EMBEDDING_DIM",
    # Lazy loader for OpenAI
    "get_openai_embedder",
]
