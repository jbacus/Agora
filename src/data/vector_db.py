"""
Vector database interface for storing and retrieving embeddings.
Supports both ChromaDB (local) and Pinecone (cloud).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import chromadb
from loguru import logger

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone not available. Install with: pip install pinecone-client")

from .models import Author, TextChunk


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the database connection."""
        pass

    @abstractmethod
    def create_collection(self, name: str, dimension: int) -> None:
        """Create a new collection/index."""
        pass

    @abstractmethod
    def insert_chunks(self, chunks: List[TextChunk]) -> None:
        """Insert text chunks with embeddings."""
        pass

    @abstractmethod
    def insert_author_profile(self, author: Author) -> None:
        """Insert author expertise profile vector."""
        pass

    @abstractmethod
    def search_chunks(
        self,
        query_vector: List[float],
        author_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Tuple[TextChunk, float]]:
        """Search for similar chunks, optionally filtered by author."""
        pass

    @abstractmethod
    def get_author_profiles(self) -> Dict[str, List[float]]:
        """Get all author expertise profile vectors."""
        pass

    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """Delete a collection/index."""
        pass


class ChromaVectorDB(VectorDatabase):
    """ChromaDB implementation (local, embedded database)."""

    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """
        Initialize ChromaDB client.

        Args:
            persist_directory: Directory to persist the database
        """
        self.persist_directory = persist_directory
        self.client: Optional[chromadb.Client] = None
        self.chunks_collection = None
        self.authors_collection = None
        logger.info(f"Initializing ChromaDB at {persist_directory}")

    def initialize(self) -> None:
        """Initialize ChromaDB client and collections."""
        # Use PersistentClient for chromadb-client compatibility
        self.client = chromadb.PersistentClient(
            path=self.persist_directory
        )

        # Get or create collections
        self.chunks_collection = self.client.get_or_create_collection(
            name="text_chunks",
            metadata={"description": "Text chunks from author works"}
        )

        self.authors_collection = self.client.get_or_create_collection(
            name="author_profiles",
            metadata={"description": "Author expertise profile vectors"}
        )

        logger.info("ChromaDB initialized successfully")

    def create_collection(self, name: str, dimension: int) -> None:
        """Create a new collection."""
        if self.client is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        self.client.get_or_create_collection(name=name)
        logger.info(f"Created collection: {name}")

    def insert_chunks(self, chunks: List[TextChunk]) -> None:
        """Insert text chunks with embeddings."""
        if self.chunks_collection is None:
            raise RuntimeError("Chunks collection not initialized")

        ids = [chunk.id for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "author_id": chunk.author_id,
                **chunk.metadata
            }
            for chunk in chunks
        ]

        self.chunks_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        logger.info(f"Inserted {len(chunks)} chunks into ChromaDB")

    def insert_author_profile(self, author: Author) -> None:
        """Insert author expertise profile vector."""
        if self.authors_collection is None:
            raise RuntimeError("Authors collection not initialized")

        if author.expertise_vector is None:
            raise ValueError(f"Author {author.id} has no expertise vector")

        self.authors_collection.add(
            ids=[author.id],
            embeddings=[author.expertise_vector],
            documents=[author.name],
            metadatas=[{
                "name": author.name,
                "expertise_domains": ",".join(author.expertise_domains),
                "bio": author.bio or ""
            }]
        )

        logger.info(f"Inserted author profile: {author.name} ({author.id})")

    def search_chunks(
        self,
        query_vector: List[float],
        author_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Tuple[TextChunk, float]]:
        """Search for similar chunks."""
        if self.chunks_collection is None:
            raise RuntimeError("Chunks collection not initialized")

        where_filter = {"author_id": author_id} if author_id else None

        results = self.chunks_collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_filter
        )

        # Parse results into TextChunk objects
        chunks_with_scores = []
        if results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                chunk = TextChunk(
                    id=chunk_id,
                    author_id=results['metadatas'][0][i]['author_id'],
                    text=results['documents'][0][i],
                    metadata={k: v for k, v in results['metadatas'][0][i].items()
                             if k != 'author_id'}
                )
                score = 1.0 - results['distances'][0][i]  # Convert distance to similarity
                chunks_with_scores.append((chunk, score))

        return chunks_with_scores

    def get_author_profiles(self) -> Dict[str, List[float]]:
        """Get all author expertise profile vectors."""
        if self.authors_collection is None:
            raise RuntimeError("Authors collection not initialized")

        # Get all authors
        results = self.authors_collection.get(include=["embeddings"])

        profiles = {}
        if results['ids']:
            for i, author_id in enumerate(results['ids']):
                profiles[author_id] = results['embeddings'][i]

        logger.info(f"Retrieved {len(profiles)} author profiles")
        return profiles

    def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        if self.client is None:
            raise RuntimeError("Database not initialized")

        self.client.delete_collection(name=name)
        logger.info(f"Deleted collection: {name}")


class PineconeVectorDB(VectorDatabase):
    """Pinecone implementation (cloud-hosted vector database)."""

    def __init__(
        self,
        api_key: str,
        environment: str,
        index_name: str = "virtual-debate-panel"
    ):
        """
        Initialize Pinecone client.

        Args:
            api_key: Pinecone API key
            environment: Pinecone environment (e.g., 'us-west1-gcp')
            index_name: Name of the index
        """
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone not installed. Install with: pip install pinecone-client")

        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.index = None
        logger.info(f"Initializing Pinecone in {environment}")

    def initialize(self) -> None:
        """Initialize Pinecone connection."""
        pinecone.init(api_key=self.api_key, environment=self.environment)

        # Check if index exists
        if self.index_name not in pinecone.list_indexes():
            raise ValueError(
                f"Index '{self.index_name}' does not exist. "
                f"Create it first with create_collection()"
            )

        self.index = pinecone.Index(self.index_name)
        logger.info(f"Connected to Pinecone index: {self.index_name}")

    def create_collection(self, name: str, dimension: int) -> None:
        """Create a new Pinecone index."""
        pinecone.create_index(
            name=name,
            dimension=dimension,
            metric="cosine"
        )
        logger.info(f"Created Pinecone index: {name} (dimension={dimension})")

    def insert_chunks(self, chunks: List[TextChunk]) -> None:
        """Insert text chunks with embeddings."""
        if self.index is None:
            raise RuntimeError("Pinecone index not initialized")

        vectors = [
            (
                chunk.id,
                chunk.embedding,
                {
                    "author_id": chunk.author_id,
                    "text": chunk.text,
                    "type": "chunk",
                    **chunk.metadata
                }
            )
            for chunk in chunks
        ]

        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)

        logger.info(f"Inserted {len(chunks)} chunks into Pinecone")

    def insert_author_profile(self, author: Author) -> None:
        """Insert author expertise profile vector."""
        if self.index is None:
            raise RuntimeError("Pinecone index not initialized")

        if author.expertise_vector is None:
            raise ValueError(f"Author {author.id} has no expertise vector")

        self.index.upsert(
            vectors=[
                (
                    f"author_{author.id}",
                    author.expertise_vector,
                    {
                        "author_id": author.id,
                        "name": author.name,
                        "type": "author_profile",
                        "expertise_domains": ",".join(author.expertise_domains)
                    }
                )
            ]
        )

        logger.info(f"Inserted author profile: {author.name} ({author.id})")

    def search_chunks(
        self,
        query_vector: List[float],
        author_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Tuple[TextChunk, float]]:
        """Search for similar chunks."""
        if self.index is None:
            raise RuntimeError("Pinecone index not initialized")

        filter_dict = {"type": "chunk"}
        if author_id:
            filter_dict["author_id"] = author_id

        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            filter=filter_dict,
            include_metadata=True
        )

        chunks_with_scores = []
        for match in results['matches']:
            metadata = match['metadata']
            chunk = TextChunk(
                id=match['id'],
                author_id=metadata['author_id'],
                text=metadata['text'],
                metadata={k: v for k, v in metadata.items()
                         if k not in ['author_id', 'text', 'type']}
            )
            chunks_with_scores.append((chunk, match['score']))

        return chunks_with_scores

    def get_author_profiles(self) -> Dict[str, List[float]]:
        """Get all author expertise profile vectors."""
        if self.index is None:
            raise RuntimeError("Pinecone index not initialized")

        # Query for all author profiles
        # Note: Pinecone doesn't have a direct "get all" method,
        # so we fetch by type filter with a large top_k
        results = self.index.query(
            vector=[0.0] * self.index.describe_index_stats()['dimension'],
            top_k=100,
            filter={"type": "author_profile"},
            include_metadata=True
        )

        profiles = {}
        for match in results['matches']:
            author_id = match['metadata']['author_id']
            # Note: Pinecone doesn't return vectors in query results by default
            # We'd need to fetch them separately or store them differently
            logger.warning("Pinecone doesn't return vectors in query results")
            profiles[author_id] = []  # Placeholder

        return profiles

    def delete_collection(self, name: str) -> None:
        """Delete a Pinecone index."""
        pinecone.delete_index(name)
        logger.info(f"Deleted Pinecone index: {name}")


def get_vector_db(
    db_type: str,
    **kwargs
) -> VectorDatabase:
    """
    Factory function to get the appropriate vector database.

    Args:
        db_type: Type of database ('chromadb' or 'pinecone')
        **kwargs: Additional arguments for the database constructor

    Returns:
        VectorDatabase instance
    """
    if db_type == "chromadb":
        return ChromaVectorDB(**kwargs)
    elif db_type == "pinecone":
        return PineconeVectorDB(**kwargs)
    else:
        raise ValueError(f"Unknown database type: {db_type}")
