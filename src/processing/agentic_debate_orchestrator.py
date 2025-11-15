"""
Agentic debate orchestrator with tool-using author agents.

This module implements an enhanced debate system where authors are autonomous agents
that can use tools to search their works, reason through multi-step arguments, and
learn from the debate context.
"""
import asyncio
import time
from typing import Any, Dict, List, Optional
from enum import Enum

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


class ToolType(Enum):
    """Available tools for debate agents."""
    SEARCH_OWN_WORKS = "search_own_works"
    SEARCH_OTHER_WORKS = "search_other_works"
    RECALL_PREVIOUS_ROUND = "recall_previous_round"
    ANALYZE_ARGUMENT = "analyze_argument"


class DebateAgent:
    """
    Autonomous debate agent representing an author.

    Capabilities:
    - Search own works for relevant passages
    - Search other authors' works to understand their perspective
    - Recall and analyze previous debate rounds
    - Multi-step reasoning about arguments
    - Learn from debate context
    """

    def __init__(
        self,
        author: Author,
        rag_pipeline: RAGPipeline,
        llm_client: LLMClient,
        knowledge_base: 'SharedDebateKnowledgeBase',
        max_response_tokens: int = 400,
        temperature: float = 0.7
    ):
        """
        Initialize debate agent.

        Args:
            author: Author this agent represents
            rag_pipeline: RAG pipeline for retrieval
            llm_client: LLM client for generation
            knowledge_base: Shared knowledge across debate
            max_response_tokens: Max tokens in response
            temperature: LLM temperature
        """
        self.author = author
        self.rag_pipeline = rag_pipeline
        self.llm_client = llm_client
        self.knowledge_base = knowledge_base
        self.max_response_tokens = max_response_tokens
        self.temperature = temperature

        # Agent's internal state
        self.tool_use_history: List[Dict[str, Any]] = []
        self.reasoning_chain: List[str] = []

        logger.info(f"Initialized DebateAgent for {author.name}")

    async def search_own_works(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search this author's own works for relevant passages.

        Args:
            query_text: Search query
            top_k: Number of results

        Returns:
            List of chunks with metadata
        """
        start_time = time.time()

        loop = asyncio.get_event_loop()

        # Get query embedding
        query_embedding = await loop.run_in_executor(
            None,
            self.rag_pipeline.embedding_provider.embed_text,
            query_text
        )

        # Search this author's chunks
        chunks_with_scores = await loop.run_in_executor(
            None,
            self.rag_pipeline.vector_db.search_chunks,
            query_embedding,
            self.author.id,
            top_k
        )

        results = [
            {
                "id": chunk.id,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "score": score
            }
            for chunk, score in chunks_with_scores
        ]

        elapsed_ms = (time.time() - start_time) * 1000

        # Record tool use
        self.tool_use_history.append({
            "tool": ToolType.SEARCH_OWN_WORKS.value,
            "query": query_text,
            "results_count": len(results),
            "time_ms": elapsed_ms
        })

        logger.info(
            f"{self.author.name} searched own works: '{query_text}' "
            f"-> {len(results)} results ({elapsed_ms:.0f}ms)"
        )

        return results

    async def search_other_works(
        self,
        author_id: str,
        query_text: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search another author's works to understand their perspective.

        Args:
            author_id: Other author's ID
            query_text: Search query
            top_k: Number of results

        Returns:
            List of chunks with metadata
        """
        start_time = time.time()

        loop = asyncio.get_event_loop()

        # Get query embedding
        query_embedding = await loop.run_in_executor(
            None,
            self.rag_pipeline.embedding_provider.embed_text,
            query_text
        )

        # Search other author's chunks
        chunks_with_scores = await loop.run_in_executor(
            None,
            self.rag_pipeline.vector_db.search_chunks,
            query_embedding,
            author_id,
            top_k
        )

        results = [
            {
                "id": chunk.id,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "score": score
            }
            for chunk, score in chunks_with_scores
        ]

        elapsed_ms = (time.time() - start_time) * 1000

        # Record tool use
        self.tool_use_history.append({
            "tool": ToolType.SEARCH_OTHER_WORKS.value,
            "author_id": author_id,
            "query": query_text,
            "results_count": len(results),
            "time_ms": elapsed_ms
        })

        logger.info(
            f"{self.author.name} searched {author_id}'s works: '{query_text}' "
            f"-> {len(results)} results ({elapsed_ms:.0f}ms)"
        )

        return results

    async def recall_previous_round(
        self,
        round_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Recall what was said in a previous round.

        Args:
            round_number: Round to recall

        Returns:
            Round data if available
        """
        round_data = await self.knowledge_base.get_round(round_number)

        if round_data:
            self.tool_use_history.append({
                "tool": ToolType.RECALL_PREVIOUS_ROUND.value,
                "round_number": round_number,
                "found": True
            })
            logger.info(f"{self.author.name} recalled round {round_number}")

        return round_data

    async def analyze_argument(
        self,
        argument_text: str,
        author_name: str
    ) -> str:
        """
        Analyze an argument from another author.

        Args:
            argument_text: The argument to analyze
            author_name: Who made the argument

        Returns:
            Analysis of the argument
        """
        start_time = time.time()

        analysis_prompt = f"""Analyze this argument from {author_name}:

"{argument_text}"

Provide a brief analysis identifying:
1. The main claim
2. Key supporting points
3. Potential weaknesses or areas for critique
4. Points of agreement with your own perspective

Keep your analysis to 2-3 sentences."""

        loop = asyncio.get_event_loop()

        analysis = await loop.run_in_executor(
            None,
            self.llm_client.generate,
            self.author.system_prompt,
            analysis_prompt,
            200,  # Short analysis
            self.temperature
        )

        elapsed_ms = (time.time() - start_time) * 1000

        self.tool_use_history.append({
            "tool": ToolType.ANALYZE_ARGUMENT.value,
            "author": author_name,
            "time_ms": elapsed_ms
        })

        self.reasoning_chain.append(
            f"Analyzed {author_name}'s argument: {analysis}"
        )

        logger.info(
            f"{self.author.name} analyzed {author_name}'s argument "
            f"({elapsed_ms:.0f}ms)"
        )

        return analysis

    async def generate_response(
        self,
        query: Query,
        other_responses: List[AuthorResponse],
        round_number: int,
        use_tools: bool = True
    ) -> AuthorResponse:
        """
        Generate a debate response using multi-step reasoning and tools.

        Args:
            query: Original query
            other_responses: Other authors' responses
            round_number: Current round
            use_tools: Whether to use tools for enhanced reasoning

        Returns:
            Generated response
        """
        start_time = time.time()

        # Reset reasoning chain for this response
        self.reasoning_chain = []

        if use_tools and round_number > 1:
            # Step 1: Search own works for relevant support
            self.reasoning_chain.append(
                f"Searching my works for insights on: {query.text}"
            )
            own_results = await self.search_own_works(query.text, top_k=5)

            # Step 2: Analyze other authors' arguments
            for response in other_responses[:2]:  # Limit to 2 to control cost
                self.reasoning_chain.append(
                    f"Analyzing {response.author_name}'s argument"
                )
                analysis = await self.analyze_argument(
                    response.response_text,
                    response.author_name
                )

            # Step 3: If there's a specific point to address, search for it
            if other_responses:
                first_response = other_responses[0]
                # Extract key concept from their response (simple heuristic)
                key_words = first_response.response_text.split()[:20]
                search_query = " ".join(key_words)

                self.reasoning_chain.append(
                    "Searching for additional context on their key points"
                )
                additional_results = await self.search_own_works(
                    search_query,
                    top_k=3
                )

                # Combine results
                all_chunks = own_results + additional_results
            else:
                all_chunks = own_results
        else:
            # First round: Just search for relevant chunks
            all_chunks_raw = await self.search_own_works(query.text, top_k=5)
            all_chunks = all_chunks_raw

        # Build debate prompt with reasoning chain
        debate_prompt = self._build_agentic_prompt(
            query=query,
            other_responses=other_responses,
            reasoning_chain=self.reasoning_chain,
            round_number=round_number
        )

        # Generate response
        loop = asyncio.get_event_loop()

        response_text = await loop.run_in_executor(
            None,
            self.llm_client.generate,
            self.author.system_prompt,
            debate_prompt,
            self.max_response_tokens,
            self.temperature
        )

        # Build retrieved chunks for citations
        retrieved_chunks = [
            {"id": chunk.get("id", ""), "metadata": chunk.get("metadata", {})}
            for chunk in all_chunks
        ]

        elapsed_ms = (time.time() - start_time) * 1000

        # Record in knowledge base
        await self.knowledge_base.record_response(
            round_number=round_number,
            author_id=self.author.id,
            author_name=self.author.name,
            response_text=response_text,
            tool_uses=len(self.tool_use_history),
            reasoning_steps=len(self.reasoning_chain)
        )

        logger.info(
            f"Generated agentic response for {self.author.name} "
            f"(round {round_number}, {len(self.tool_use_history)} tool uses, "
            f"{len(self.reasoning_chain)} reasoning steps, {elapsed_ms:.0f}ms)"
        )

        return AuthorResponse(
            author_id=self.author.id,
            author_name=self.author.name,
            response_text=response_text,
            relevance_score=1.0,
            retrieved_chunks=retrieved_chunks,
            generation_time_ms=elapsed_ms
        )

    def _build_agentic_prompt(
        self,
        query: Query,
        other_responses: List[AuthorResponse],
        reasoning_chain: List[str],
        round_number: int
    ) -> str:
        """
        Build prompt for agentic debate response.

        Args:
            query: Original query
            other_responses: Other authors' responses
            reasoning_chain: Agent's reasoning steps
            round_number: Current round

        Returns:
            Formatted prompt
        """
        prompt_parts = [
            f"The original question was: {query.text}",
            ""
        ]

        # Include reasoning chain if available
        if reasoning_chain:
            prompt_parts.append("Your internal reasoning process:")
            for i, step in enumerate(reasoning_chain, 1):
                prompt_parts.append(f"  {i}. {step}")
            prompt_parts.append("")

        # Include other responses if this is not the first round
        if other_responses:
            prompt_parts.append("Other thinkers have provided these perspectives:")
            prompt_parts.append("")

            for i, response in enumerate(other_responses, 1):
                prompt_parts.append(f"{i}. {response.author_name} said:")
                prompt_parts.append(f'"{response.response_text}"')
                prompt_parts.append("")

        # Instructions based on round
        if round_number == 1:
            prompt_parts.extend([
                "Provide your initial perspective on this question.",
                "Draw from your works and philosophy.",
                "Be concise and substantive."
            ])
        else:
            prompt_parts.extend([
                "Now respond to these perspectives. You may:",
                "- Critique or challenge their arguments",
                "- Build upon their ideas",
                "- Highlight where you agree or disagree",
                "- Offer your own distinct perspective",
                "",
                "Use your characteristic voice and style.",
                "Limit your response to 2-3 paragraphs.",
                "Be direct and substantive in engaging with the other viewpoints."
            ])

        return "\n".join(prompt_parts)


class SharedDebateKnowledgeBase:
    """
    Shared knowledge base for all debate agents.

    Tracks:
    - All responses by round
    - Tool usage patterns
    - Reasoning chains
    - Cross-author references
    """

    def __init__(self):
        """Initialize shared knowledge base."""
        self.rounds: Dict[int, List[Dict[str, Any]]] = {}
        self.tool_stats: Dict[str, int] = {
            tool.value: 0 for tool in ToolType
        }
        self._lock = asyncio.Lock()

        logger.info("Initialized SharedDebateKnowledgeBase")

    async def record_response(
        self,
        round_number: int,
        author_id: str,
        author_name: str,
        response_text: str,
        tool_uses: int,
        reasoning_steps: int
    ):
        """
        Record a debate response.

        Args:
            round_number: Round number
            author_id: Author ID
            author_name: Author name
            response_text: Response text
            tool_uses: Number of tools used
            reasoning_steps: Number of reasoning steps
        """
        async with self._lock:
            if round_number not in self.rounds:
                self.rounds[round_number] = []

            self.rounds[round_number].append({
                "author_id": author_id,
                "author_name": author_name,
                "response_text": response_text,
                "tool_uses": tool_uses,
                "reasoning_steps": reasoning_steps,
                "timestamp": time.time()
            })

            logger.debug(
                f"Recorded response from {author_name} in round {round_number}"
            )

    async def get_round(self, round_number: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get all responses from a specific round.

        Args:
            round_number: Round to retrieve

        Returns:
            List of responses or None
        """
        async with self._lock:
            return self.rounds.get(round_number)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get debate statistics.

        Returns:
            Statistics dictionary
        """
        async with self._lock:
            total_responses = sum(len(r) for r in self.rounds.values())
            total_tools = sum(
                sum(resp.get("tool_uses", 0) for resp in responses)
                for responses in self.rounds.values()
            )

            return {
                "total_rounds": len(self.rounds),
                "total_responses": total_responses,
                "total_tool_uses": total_tools,
                "tool_stats": self.tool_stats.copy()
            }


class AgenticDebateOrchestrator:
    """
    Orchestrates agentic debates with tool-using author agents.

    This orchestrator enables:
    - Authors using tools to search and analyze
    - Multi-step reasoning chains
    - Collaborative learning via shared knowledge base
    - Enhanced debate quality through deeper engagement
    """

    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        llm_client: LLMClient,
        max_response_tokens: int = 400,
        temperature: float = 0.7
    ):
        """
        Initialize agentic debate orchestrator.

        Args:
            rag_pipeline: RAG pipeline for retrieval
            llm_client: LLM client for generation
            max_response_tokens: Max tokens per response
            temperature: LLM temperature
        """
        self.rag_pipeline = rag_pipeline
        self.llm_client = llm_client
        self.max_response_tokens = max_response_tokens
        self.temperature = temperature

        logger.info("Initialized AgenticDebateOrchestrator")

    async def orchestrate_debate(
        self,
        query: Query,
        authors: List[Author],
        initial_responses: List[AuthorResponse],
        query_embedding: List[float],
        selection_method: str,
        num_rounds: int = 2,
        use_tools: bool = True
    ) -> DebateResponse:
        """
        Orchestrate an agentic multi-round debate.

        Args:
            query: Original user query
            authors: List of participating authors
            initial_responses: Initial responses from each author
            query_embedding: Pre-computed query embedding
            selection_method: Method used for author selection
            num_rounds: Total number of rounds
            use_tools: Whether agents should use tools

        Returns:
            Complete debate response with all rounds
        """
        start_time = time.time()

        # Create shared knowledge base
        knowledge_base = SharedDebateKnowledgeBase()

        # Create debate agents for each author
        agents = {
            author.id: DebateAgent(
                author=author,
                rag_pipeline=self.rag_pipeline,
                llm_client=self.llm_client,
                knowledge_base=knowledge_base,
                max_response_tokens=self.max_response_tokens,
                temperature=self.temperature
            )
            for author in authors
        }

        # Round 1: Initial responses (already provided)
        rounds = [
            DebateRound(
                round_number=1,
                round_type="initial",
                author_responses=initial_responses
            )
        ]

        # Record initial responses in knowledge base
        for response in initial_responses:
            await knowledge_base.record_response(
                round_number=1,
                author_id=response.author_id,
                author_name=response.author_name,
                response_text=response.response_text,
                tool_uses=0,
                reasoning_steps=0
            )

        logger.info(
            f"Starting agentic debate: {len(authors)} authors, "
            f"{num_rounds} rounds, tools={'enabled' if use_tools else 'disabled'}"
        )

        # Additional rounds: Agentic responses with tools
        for round_num in range(2, num_rounds + 1):
            logger.info(f"Generating agentic round {round_num} responses...")

            # Get previous round responses
            previous_responses = rounds[-1].author_responses

            # Generate responses using agents
            round_responses = await self._generate_agentic_round(
                query=query,
                agents=agents,
                previous_responses=previous_responses,
                round_number=round_num,
                use_tools=use_tools
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

        # Get final stats
        stats = await knowledge_base.get_stats()

        logger.info(
            f"Agentic debate completed: {len(rounds)} rounds, "
            f"{len(authors)} authors, {stats['total_tool_uses']} tool uses, "
            f"{total_time_ms:.0f}ms"
        )

        return DebateResponse(
            query=query,
            rounds=rounds,
            total_time_ms=total_time_ms,
            selection_method=f"{selection_method} (agentic)"
        )

    async def _generate_agentic_round(
        self,
        query: Query,
        agents: Dict[str, DebateAgent],
        previous_responses: List[AuthorResponse],
        round_number: int,
        use_tools: bool
    ) -> List[AuthorResponse]:
        """
        Generate responses for an agentic debate round.

        Args:
            query: Original query
            agents: Dictionary of debate agents
            previous_responses: Previous round responses
            round_number: Current round number
            use_tools: Whether to use tools

        Returns:
            List of author responses
        """
        # Generate responses concurrently
        tasks = []

        for agent in agents.values():
            # Get other authors' responses (exclude this agent's author)
            other_responses = [
                resp for resp in previous_responses
                if resp.author_id != agent.author.id
            ]

            task = agent.generate_response(
                query=query,
                other_responses=other_responses,
                round_number=round_number,
                use_tools=use_tools
            )
            tasks.append(task)

        # Execute all agents concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                agent_name = list(agents.values())[i].author.name
                logger.error(
                    f"Failed to generate agentic response for {agent_name}: "
                    f"{response}"
                )
            else:
                valid_responses.append(response)

        return valid_responses
