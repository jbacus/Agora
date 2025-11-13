"""
Semantic router for intelligent author selection based on query relevance.
"""
from typing import Dict, List, Optional

from loguru import logger

from ..data.embeddings import EmbeddingProvider, cosine_similarity
from ..data.models import AuthorSelectionResult, Query
from ..data.vector_db import VectorDatabase


class SemanticRouter:
    """
    Routes queries to relevant authors based on semantic similarity.

    The router:
    1. Embeds the user's query
    2. Compares query embedding to author expertise profile embeddings
    3. Selects authors whose similarity exceeds the relevance threshold
    4. Falls back to top-K authors if threshold not met
    """

    def __init__(
        self,
        vector_db: VectorDatabase,
        embedding_provider: EmbeddingProvider,
        relevance_threshold: float = 0.7,
        min_authors: int = 2,
        max_authors: int = 5,
        fallback_to_top: bool = True
    ):
        """
        Initialize the semantic router.

        Args:
            vector_db: Vector database containing author profiles
            embedding_provider: Provider for generating query embeddings
            relevance_threshold: Minimum similarity score to include author
            min_authors: Minimum number of authors to select
            max_authors: Maximum number of authors to select
            fallback_to_top: Fall back to top-K if threshold not met
        """
        self.vector_db = vector_db
        self.embedding_provider = embedding_provider
        self.relevance_threshold = relevance_threshold
        self.min_authors = min_authors
        self.max_authors = max_authors
        self.fallback_to_top = fallback_to_top

        # Cache author profiles
        self._author_profiles: Optional[Dict[str, List[float]]] = None

        logger.info(
            f"Initialized SemanticRouter with threshold={relevance_threshold}, "
            f"min={min_authors}, max={max_authors}"
        )

    def _load_author_profiles(self) -> Dict[str, List[float]]:
        """Load author expertise profiles from vector database."""
        if self._author_profiles is None:
            self._author_profiles = self.vector_db.get_author_profiles()
            logger.info(f"Loaded {len(self._author_profiles)} author profiles")
        return self._author_profiles

    def select_authors(self, query: Query) -> AuthorSelectionResult:
        """
        Select relevant authors for the given query.

        Args:
            query: User query

        Returns:
            AuthorSelectionResult with selected authors and scores
        """
        # If authors are explicitly specified, use them
        if query.specified_authors:
            return self._handle_specified_authors(query)

        # Otherwise, use semantic routing
        return self._semantic_selection(query)

    def _handle_specified_authors(self, query: Query) -> AuthorSelectionResult:
        """Handle case where authors are explicitly specified."""
        query_vector = self.embedding_provider.embed_text(query.text)
        author_profiles = self._load_author_profiles()

        # Get similarity scores for specified authors
        similarity_scores = {}
        for author_id in query.specified_authors:
            if author_id in author_profiles:
                profile_vector = author_profiles[author_id]
                score = cosine_similarity(query_vector, profile_vector)
                similarity_scores[author_id] = score
            else:
                logger.warning(f"Specified author not found: {author_id}")

        return AuthorSelectionResult(
            selected_authors=list(similarity_scores.keys()),
            similarity_scores=similarity_scores,
            selection_method="specified",
            query_vector=query_vector,
            threshold_used=self.relevance_threshold
        )

    def _semantic_selection(self, query: Query) -> AuthorSelectionResult:
        """
        Perform semantic author selection based on query relevance.

        Steps:
        1. Embed the query
        2. Calculate cosine similarity with all author profiles
        3. Select authors above threshold
        4. Apply min/max constraints
        5. Fall back to top-K if needed
        """
        # Step 1: Embed query
        query_vector = self.embedding_provider.embed_text(query.text)
        logger.debug(f"Query embedded: {len(query_vector)} dimensions")

        # Step 2: Calculate similarities
        author_profiles = self._load_author_profiles()
        similarity_scores = {}

        for author_id, profile_vector in author_profiles.items():
            score = cosine_similarity(query_vector, profile_vector)
            similarity_scores[author_id] = score

        logger.debug(f"Calculated similarities for {len(similarity_scores)} authors")

        # Step 3: Filter by threshold
        threshold = query.relevance_threshold
        above_threshold = {
            author_id: score
            for author_id, score in similarity_scores.items()
            if score >= threshold
        }

        # Step 4: Apply constraints
        if len(above_threshold) >= query.min_authors:
            # We have enough authors above threshold
            selected = self._apply_max_constraint(above_threshold, query.max_authors)
            method = "threshold"
            logger.info(
                f"Selected {len(selected)} authors using threshold "
                f"(threshold={threshold:.2f})"
            )

        elif self.fallback_to_top:
            # Fall back to top-K authors
            selected = self._select_top_k(
                similarity_scores,
                max(query.min_authors, len(above_threshold))
            )
            method = "fallback_top_k"
            logger.warning(
                f"Only {len(above_threshold)} authors above threshold. "
                f"Falling back to top-{len(selected)}"
            )

        else:
            # No fallback - return what we have
            selected = above_threshold
            method = "threshold_partial"
            logger.warning(
                f"Only {len(selected)} authors above threshold "
                f"(min={query.min_authors})"
            )

        return AuthorSelectionResult(
            selected_authors=list(selected.keys()),
            similarity_scores=similarity_scores,
            selection_method=method,
            query_vector=query_vector,
            threshold_used=threshold
        )

    def _apply_max_constraint(
        self,
        scores: Dict[str, float],
        max_authors: int
    ) -> Dict[str, float]:
        """
        Apply maximum author constraint by selecting top scorers.

        Args:
            scores: Author ID to similarity score mapping
            max_authors: Maximum number of authors

        Returns:
            Filtered dictionary with top authors
        """
        if len(scores) <= max_authors:
            return scores

        # Sort by score descending and take top-K
        sorted_authors = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_authors]

        return dict(sorted_authors)

    def _select_top_k(
        self,
        scores: Dict[str, float],
        k: int
    ) -> Dict[str, float]:
        """
        Select top-K authors by similarity score.

        Args:
            scores: Author ID to similarity score mapping
            k: Number of authors to select

        Returns:
            Dictionary with top-K authors
        """
        sorted_authors = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:k]

        return dict(sorted_authors)

    def update_threshold(self, new_threshold: float) -> None:
        """Update the relevance threshold."""
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        self.relevance_threshold = new_threshold
        logger.info(f"Updated relevance threshold to {new_threshold:.2f}")

    def clear_cache(self) -> None:
        """Clear the cached author profiles."""
        self._author_profiles = None
        logger.info("Cleared author profile cache")

    def get_author_rankings(self, query: Query) -> List[tuple[str, float]]:
        """
        Get all authors ranked by relevance to query.

        Args:
            query: User query

        Returns:
            List of (author_id, score) tuples sorted by score descending
        """
        query_vector = self.embedding_provider.embed_text(query.text)
        author_profiles = self._load_author_profiles()

        scores = [
            (author_id, cosine_similarity(query_vector, profile_vector))
            for author_id, profile_vector in author_profiles.items()
        ]

        return sorted(scores, key=lambda x: x[1], reverse=True)
