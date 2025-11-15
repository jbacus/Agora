"""
Retrieval-Augmented Generation (RAG) pipeline for author responses.
"""
import asyncio
import time
from typing import List, Tuple

from loguru import logger

from ..data.embeddings import EmbeddingProvider
from ..data.models import Author, AuthorResponse, Query, TextChunk
from ..data.vector_db import VectorDatabase
from .llm_client import LLMClient


class RAGPipeline:
    """
    RAG pipeline for generating contextual author responses.

    Pipeline steps:
    1. Retrieve relevant text chunks for each author
    2. Construct context from retrieved chunks
    3. Generate response using LLM with author's system prompt
    4. Return formatted AuthorResponse
    """

    def __init__(
        self,
        vector_db: VectorDatabase,
        embedding_provider: EmbeddingProvider,
        llm_client: LLMClient,
        top_k_chunks: int = 5,
        max_response_tokens: int = 300,
        temperature: float = 0.7
    ):
        """
        Initialize RAG pipeline.

        Args:
            vector_db: Vector database for chunk retrieval
            embedding_provider: Provider for query embeddings
            llm_client: LLM client for generation
            top_k_chunks: Number of chunks to retrieve per author
            max_response_tokens: Maximum tokens in LLM response
            temperature: LLM temperature parameter
        """
        self.vector_db = vector_db
        self.embedding_provider = embedding_provider
        self.llm_client = llm_client
        self.top_k_chunks = top_k_chunks
        self.max_response_tokens = max_response_tokens
        self.temperature = temperature

        logger.info(
            f"Initialized RAG pipeline with top_k={top_k_chunks}, "
            f"max_tokens={max_response_tokens}"
        )

    def generate_response(
        self,
        query: Query,
        author: Author,
        query_embedding: List[float]
    ) -> AuthorResponse:
        """
        Generate a response from a single author using RAG.

        Args:
            query: User query
            author: Author to generate response for
            query_embedding: Pre-computed query embedding

        Returns:
            AuthorResponse with generated text and metadata
        """
        start_time = time.time()

        # Step 1: Retrieve relevant chunks
        chunks_with_scores = self.vector_db.search_chunks(
            query_vector=query_embedding,
            author_id=author.id,
            top_k=self.top_k_chunks
        )

        logger.debug(
            f"Retrieved {len(chunks_with_scores)} chunks for {author.name}"
        )

        # Step 2: Construct context
        context = self._build_context(chunks_with_scores)

        # Step 3: Build prompt
        user_prompt = self._build_user_prompt(query.text, context)

        # Step 4: Generate response
        response_text = self.llm_client.generate(
            system_prompt=author.system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.max_response_tokens,
            temperature=self.temperature
        )

        # Calculate relevance score (average of top chunk scores)
        relevance_score = (
            sum(score for _, score in chunks_with_scores) / len(chunks_with_scores)
            if chunks_with_scores else 0.0
        )

        elapsed_ms = (time.time() - start_time) * 1000

        # Build retrieved chunks with metadata
        retrieved_chunks = [
            {"id": chunk.id, "metadata": chunk.metadata}
            for chunk, _ in chunks_with_scores
        ]

        logger.info(
            f"Generated response for {author.name} "
            f"(relevance={relevance_score:.2f}, time={elapsed_ms:.0f}ms)"
        )

        return AuthorResponse(
            author_id=author.id,
            author_name=author.name,
            response_text=response_text,
            relevance_score=relevance_score,
            retrieved_chunks=retrieved_chunks,
            generation_time_ms=elapsed_ms
        )

    async def generate_response_async(
        self,
        query: Query,
        author: Author,
        query_embedding: List[float]
    ) -> AuthorResponse:
        """
        Async version of generate_response for concurrent processing.

        Args:
            query: User query
            author: Author to generate response for
            query_embedding: Pre-computed query embedding

        Returns:
            AuthorResponse with generated text and metadata
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_response,
            query,
            author,
            query_embedding
        )

    async def generate_responses_concurrent(
        self,
        query: Query,
        authors: List[Author],
        query_embedding: List[float]
    ) -> List[AuthorResponse]:
        """
        Generate responses from multiple authors concurrently.

        Args:
            query: User query
            authors: List of authors to generate responses for
            query_embedding: Pre-computed query embedding

        Returns:
            List of AuthorResponse objects
        """
        start_time = time.time()

        # Create tasks for concurrent execution
        tasks = [
            self.generate_response_async(query, author, query_embedding)
            for author in authors
        ]

        # Execute all tasks concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out any exceptions
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(
                    f"Failed to generate response for {authors[i].name}: {response}"
                )
            else:
                valid_responses.append(response)

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Generated {len(valid_responses)}/{len(authors)} responses "
            f"concurrently (total_time={elapsed_ms:.0f}ms)"
        )

        return valid_responses

    def _build_context(
        self,
        chunks_with_scores: List[Tuple[TextChunk, float]]
    ) -> str:
        """
        Build context string from retrieved chunks.

        Args:
            chunks_with_scores: List of (chunk, score) tuples

        Returns:
            Formatted context string
        """
        if not chunks_with_scores:
            return "No relevant context found."

        context_parts = []
        for i, (chunk, score) in enumerate(chunks_with_scores, 1):
            # Include metadata if available
            source_info = ""
            if "book" in chunk.metadata:
                source_info = f" (from {chunk.metadata['book']})"

            context_parts.append(
                f"[{i}]{source_info}: {chunk.text}"
            )

        return "\n\n".join(context_parts)

    def _build_user_prompt(self, query_text: str, context: str) -> str:
        """
        Build the user prompt combining query and context.

        Args:
            query_text: User's query
            context: Retrieved context

        Returns:
            Formatted user prompt
        """
        prompt = f"""Based on the following excerpts from your works, please respond to the user's query.

RELEVANT EXCERPTS:
{context}

USER QUERY:
{query_text}

Please provide a response in your characteristic voice and style. Limit your response to a maximum of 3 paragraphs. Focus on directly addressing the query while drawing from the provided context."""

        return prompt

    def generate_streaming_response(
        self,
        query: Query,
        author: Author,
        query_embedding: List[float]
    ):
        """
        Generate a streaming response from an author using RAG.

        Args:
            query: User query
            author: Author to generate response for
            query_embedding: Pre-computed query embedding

        Yields:
            Chunks of generated text
        """
        # Retrieve relevant chunks
        chunks_with_scores = self.vector_db.search_chunks(
            query_vector=query_embedding,
            author_id=author.id,
            top_k=self.top_k_chunks
        )

        # Construct context and prompt
        context = self._build_context(chunks_with_scores)
        user_prompt = self._build_user_prompt(query.text, context)

        # Stream generation
        for chunk in self.llm_client.generate_streaming(
            system_prompt=author.system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.max_response_tokens,
            temperature=self.temperature
        ):
            yield chunk
