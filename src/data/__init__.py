"""
Data layer for the Virtual Debate Panel.
Handles vector database operations, embeddings, and data models.
"""
from .embeddings import (
    EmbeddingProvider,
    GeminiEmbeddings,
    LocalEmbeddings,
    OpenAIEmbeddings,
    cosine_similarity,
    get_embedding_provider,
)
from .models import (
    Author,
    AuthorExpertise,
    AuthorResponse,
    AuthorSelectionResult,
    DebatePanelResponse,
    Query,
    TextChunk,
    VoiceCharacteristics,
)
from .vector_db import (
    ChromaVectorDB,
    PineconeVectorDB,
    VectorDatabase,
    get_vector_db,
)

__all__ = [
    # Models
    "Author",
    "AuthorExpertise",
    "AuthorResponse",
    "AuthorSelectionResult",
    "DebatePanelResponse",
    "Query",
    "TextChunk",
    "VoiceCharacteristics",
    # Vector DB
    "VectorDatabase",
    "ChromaVectorDB",
    "PineconeVectorDB",
    "get_vector_db",
    # Embeddings
    "EmbeddingProvider",
    "GeminiEmbeddings",
    "OpenAIEmbeddings",
    "LocalEmbeddings",
    "get_embedding_provider",
    "cosine_similarity",
]
