"""
Debate orchestrator for multi-round author debates.
"""
import asyncio
import time
from typing import List

from loguru import logger

from ..data.models import (
    Author,
    AuthorResponse,
    DebateResponse,
    DebateRound,
    Query,
)
from .llm_client import LLMClient
from .rag_pipeline import RAGPipeline


class DebateOrchestrator:
    """
    Orchestrates multi-round debates between authors.

    The debate flow:
    1. Round 1: Initial responses to the original query
    2. Round 2+: Each author responds to other authors' previous responses
    """

    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        llm_client: LLMClient,
        max_response_tokens: int = 300,
        temperature: float = 0.7
    ):
        """
        Initialize debate orchestrator.

        Args:
            rag_pipeline: RAG pipeline for generating responses
            llm_client: LLM client for generating debate responses
            max_response_tokens: Maximum tokens per response
            temperature: LLM temperature parameter
        """
        self.rag_pipeline = rag_pipeline
        self.llm_client = llm_client
        self.max_response_tokens = max_response_tokens
        self.temperature = temperature

        logger.info("Initialized DebateOrchestrator")

    async def orchestrate_debate(
        self,
        query: Query,
        authors: List[Author],
        initial_responses: List[AuthorResponse],
        query_embedding: List[float],
        selection_method: str,
        num_rounds: int = 2
    ) -> DebateResponse:
        """
        Orchestrate a multi-round debate between authors.

        Args:
            query: Original user query
            authors: List of participating authors
            initial_responses: Initial responses from each author
            query_embedding: Pre-computed query embedding
            selection_method: Method used for author selection
            num_rounds: Total number of rounds (including initial)

        Returns:
            Complete debate response with all rounds
        """
        start_time = time.time()

        # Round 1: Initial responses
        rounds = [
            DebateRound(
                round_number=1,
                round_type="initial",
                author_responses=initial_responses
            )
        ]

        logger.info(
            f"Starting debate with {len(authors)} authors for {num_rounds} rounds"
        )

        # Additional rounds: Rebuttals and responses
        for round_num in range(2, num_rounds + 1):
            logger.info(f"Generating round {round_num} responses...")

            # Get previous round responses
            previous_responses = rounds[-1].author_responses

            # Generate responses for this round
            round_responses = await self._generate_round_responses(
                query=query,
                authors=authors,
                previous_responses=previous_responses,
                round_number=round_num
            )

            # Create round object
            round_type = "rebuttal" if round_num == 2 else "response"
            rounds.append(
                DebateRound(
                    round_number=round_num,
                    round_type=round_type,
                    author_responses=round_responses
                )
            )

        total_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Debate completed: {len(rounds)} rounds, "
            f"{len(authors)} authors, {total_time_ms:.0f}ms"
        )

        return DebateResponse(
            query=query,
            rounds=rounds,
            total_time_ms=total_time_ms,
            selection_method=selection_method
        )

    async def _generate_round_responses(
        self,
        query: Query,
        authors: List[Author],
        previous_responses: List[AuthorResponse],
        round_number: int
    ) -> List[AuthorResponse]:
        """
        Generate responses for a debate round.

        Args:
            query: Original user query
            authors: List of participating authors
            previous_responses: Responses from the previous round
            round_number: Current round number

        Returns:
            List of author responses for this round
        """
        # Create a mapping of author_id to author object
        author_map = {author.id: author for author in authors}

        # Generate responses concurrently
        tasks = []
        for author in authors:
            # Get other authors' responses (exclude this author)
            other_responses = [
                resp for resp in previous_responses
                if resp.author_id != author.id
            ]

            task = self._generate_debate_response(
                author=author,
                query=query,
                other_responses=other_responses,
                round_number=round_number
            )
            tasks.append(task)

        # Execute all tasks concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out any exceptions
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(
                    f"Failed to generate round {round_number} response "
                    f"for {authors[i].name}: {response}"
                )
            else:
                valid_responses.append(response)

        return valid_responses

    async def _generate_debate_response(
        self,
        author: Author,
        query: Query,
        other_responses: List[AuthorResponse],
        round_number: int
    ) -> AuthorResponse:
        """
        Generate a debate response from one author.

        Args:
            author: Author generating the response
            query: Original user query
            other_responses: Responses from other authors
            round_number: Current round number

        Returns:
            Author's debate response
        """
        start_time = time.time()

        # Build debate prompt
        debate_prompt = self._build_debate_prompt(
            query=query,
            other_responses=other_responses
        )

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(
            None,
            self.llm_client.generate,
            author.system_prompt,
            debate_prompt,
            self.max_response_tokens,
            self.temperature
        )

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Generated round {round_number} response for {author.name} "
            f"(time={elapsed_ms:.0f}ms)"
        )

        return AuthorResponse(
            author_id=author.id,
            author_name=author.name,
            response_text=response_text,
            relevance_score=1.0,  # All authors are already selected
            retrieved_chunks=[],  # No RAG retrieval for debate rounds
            generation_time_ms=elapsed_ms
        )

    def _build_debate_prompt(
        self,
        query: Query,
        other_responses: List[AuthorResponse]
    ) -> str:
        """
        Build a prompt for the debate round.

        Args:
            query: Original user query
            other_responses: Responses from other authors

        Returns:
            Formatted debate prompt
        """
        prompt_parts = [
            f"The original question was: {query.text}",
            "",
            "Other thinkers have provided the following perspectives:",
            ""
        ]

        for i, response in enumerate(other_responses, 1):
            prompt_parts.append(f"{i}. {response.author_name} said:")
            prompt_parts.append(f'"{response.response_text}"')
            prompt_parts.append("")

        prompt_parts.extend([
            "Now, please respond to these perspectives. You may:",
            "- Critique or challenge their arguments",
            "- Build upon their ideas",
            "- Highlight where you agree or disagree",
            "- Offer your own distinct perspective",
            "",
            "Respond in your characteristic voice and style. "
            "Limit your response to a maximum of 3 paragraphs. "
            "Be direct and substantive in engaging with the other viewpoints."
        ])

        return "\n".join(prompt_parts)
