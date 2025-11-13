"""
Embedding generation using various providers (Google, OpenAI, local models).
"""
from abc import ABC, abstractmethod
from typing import List

import numpy as np
from loguru import logger

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI not available")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("SentenceTransformers not available")


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get the embedding dimension."""
        pass


class GeminiEmbeddings(EmbeddingProvider):
    """Google Gemini embedding provider."""

    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        """
        Initialize Gemini embeddings.

        Args:
            api_key: Google API key
            model: Embedding model name
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Generative AI not installed")

        genai.configure(api_key=api_key)
        self.model = model
        self._dimension = 768  # text-embedding-004 dimension
        logger.info(f"Initialized Gemini embeddings with model: {model}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        # Gemini supports batch embedding
        results = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = [
                genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )['embedding']
                for text in batch
            ]
            results.extend(batch_results)

        logger.info(f"Generated {len(results)} embeddings")
        return results

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension


class OpenAIEmbeddings(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-large"):
        """
        Initialize OpenAI embeddings.

        Args:
            api_key: OpenAI API key
            model: Embedding model name
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI not installed")

        self.client = OpenAI(api_key=api_key)
        self.model = model

        # Determine dimension based on model
        if "text-embedding-3-large" in model:
            self._dimension = 3072
        elif "text-embedding-3-small" in model:
            self._dimension = 1536
        elif "ada-002" in model:
            self._dimension = 1536
        else:
            self._dimension = 1536  # Default

        logger.info(f"Initialized OpenAI embeddings with model: {model}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        # OpenAI supports batch up to 2048 texts
        results = []
        batch_size = 2048

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch
            )
            batch_results = [item.embedding for item in response.data]
            results.extend(batch_results)

        logger.info(f"Generated {len(results)} embeddings")
        return results

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension


class LocalEmbeddings(EmbeddingProvider):
    """Local embedding provider using SentenceTransformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize local embeddings.

        Args:
            model_name: SentenceTransformer model name
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("SentenceTransformers not installed")

        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Initialized local embeddings with model: {model_name}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=32
        )
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0.0 to 1.0)
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)

    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0

    return float(dot_product / (norm_v1 * norm_v2))


def get_embedding_provider(
    provider: str,
    **kwargs
) -> EmbeddingProvider:
    """
    Factory function to get the appropriate embedding provider.

    Args:
        provider: Provider name ('gemini', 'openai', 'local')
        **kwargs: Additional arguments for the provider constructor

    Returns:
        EmbeddingProvider instance
    """
    if provider == "gemini":
        return GeminiEmbeddings(**kwargs)
    elif provider == "openai":
        return OpenAIEmbeddings(**kwargs)
    elif provider == "local":
        return LocalEmbeddings(**kwargs)
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
