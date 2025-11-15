"""
API routes for the Virtual Debate Panel.
"""
import asyncio
import json
import time
from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from src.data.models import Query

from .schemas import (
    AuthorListResponse,
    AuthorResponseSchema,
    DebatePanelResponseSchema,
    DebateRequest,
    DebateResponseSchema,
    DebateRoundSchema,
    QueryRequest,
)


async def generate_streaming_response(
    agent,
    query,
    other_responses,
    round_number,
    yield_func=None
):
    """
    Generate a streaming response from an agent.

    Returns dict with 'stream' generator, 'retrieved_chunks', 'relevance_score', 'generation_time_ms'
    """
    import time
    import asyncio

    start_time = time.time()

    # Build debate prompt
    from src.processing.agentic_debate_orchestrator import DebateAgent

    if isinstance(agent, DebateAgent):
        debate_prompt = agent._build_agentic_prompt(
            query=query,
            other_responses=other_responses,
            reasoning_chain=agent.reasoning_chain,
            round_number=round_number
        )
    else:
        debate_prompt = query.text

    # Retrieve relevant chunks
    loop = asyncio.get_event_loop()

    query_embedding = await loop.run_in_executor(
        None,
        agent.rag_pipeline.embedding_provider.embed_text,
        query.text
    )

    chunks_with_scores = await loop.run_in_executor(
        None,
        agent.rag_pipeline.vector_db.search_chunks,
        query_embedding,
        agent.author.id,
        agent.rag_pipeline.top_k_chunks
    )

    retrieved_chunks = [
        {"id": chunk.id, "metadata": chunk.metadata}
        for chunk, _ in chunks_with_scores
    ]

    # Create async generator for streaming
    async def stream_tokens():
        for token in agent.llm_client.generate_streaming(
            agent.author.system_prompt,
            debate_prompt,
            agent.max_response_tokens,
            agent.temperature
        ):
            yield token

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        'stream': stream_tokens(),
        'retrieved_chunks': retrieved_chunks,
        'relevance_score': 1.0,
        'generation_time_ms': elapsed_ms
    }


def create_router(services: Dict) -> APIRouter:
    """
    Create API router with injected services.

    Args:
        services: Dictionary of service instances

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api", tags=["debate-panel"])

    @router.post("/query", response_model=DebatePanelResponseSchema)
    async def query_debate_panel(request: QueryRequest):
        """
        Query the Virtual Debate Panel.

        This endpoint:
        1. Accepts a user query
        2. Selects relevant authors (automatically or from specified list)
        3. Generates responses from each author in parallel
        4. Returns formatted debate panel response

        **Phase 1 MVP**: Currently requires specified_authors to be set to ["marx"]
        """
        start_time = time.time()

        try:
            # Create Query object
            query = Query(
                text=request.text,
                specified_authors=request.specified_authors,
                max_authors=request.max_authors,
                min_authors=request.min_authors,
                relevance_threshold=request.relevance_threshold
            )

            # Get services
            semantic_router = services["semantic_router"]
            rag_pipeline = services["rag_pipeline"]
            response_aggregator = services["response_aggregator"]
            authors_dict = services["authors"]
            embedding_provider = services["embedding_provider"]

            # Step 1: Select authors
            logger.info(f"Selecting authors for query: {query.text[:50]}...")
            selection_result = semantic_router.select_authors(query)

            if not selection_result.selected_authors:
                raise HTTPException(
                    status_code=400,
                    detail="No relevant authors found for query"
                )

            logger.info(
                f"Selected {len(selection_result.selected_authors)} authors: "
                f"{', '.join(selection_result.selected_authors)}"
            )

            # Step 2: Get author objects
            selected_author_objs = [
                authors_dict[author_id]
                for author_id in selection_result.selected_authors
                if author_id in authors_dict
            ]

            if not selected_author_objs:
                raise HTTPException(
                    status_code=500,
                    detail="Selected authors not found in author database"
                )

            # Step 3: Generate responses concurrently
            logger.info("Generating responses from authors...")
            author_responses = await rag_pipeline.generate_responses_concurrent(
                query=query,
                authors=selected_author_objs,
                query_embedding=selection_result.query_vector
            )

            if not author_responses:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate any responses"
                )

            # Step 4: Aggregate responses
            total_time_ms = (time.time() - start_time) * 1000
            debate_response = response_aggregator.aggregate(
                query=query,
                author_responses=author_responses,
                total_time_ms=total_time_ms,
                selection_method=selection_result.selection_method
            )

            # Step 5: Format and return
            return DebatePanelResponseSchema(
                query_text=debate_response.query.text,
                authors=[
                    AuthorResponseSchema(
                        author_id=resp.author_id,
                        author_name=resp.author_name,
                        response_text=resp.response_text,
                        relevance_score=resp.relevance_score,
                        retrieved_chunks=resp.retrieved_chunks,
                        generation_time_ms=resp.generation_time_ms
                    )
                    for resp in debate_response.authors
                ],
                total_time_ms=debate_response.total_time_ms,
                selection_method=debate_response.selection_method,
                author_count=debate_response.author_count
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

    @router.post("/query/debate/agentic", response_model=DebateResponseSchema)
    async def query_agentic_debate(request: DebateRequest):
        """
        Start a multi-round agentic debate between authors.

        This endpoint uses the enhanced agentic debate orchestrator where:
        - Authors can use tools to search their own works
        - Authors can search other authors' works to understand their perspective
        - Authors engage in multi-step reasoning
        - Authors learn from shared debate context

        This endpoint:
        1. Accepts a user query and debate parameters
        2. Selects relevant authors (automatically or from specified list)
        3. Creates autonomous debate agents for each author
        4. Generates initial responses from each author
        5. Conducts additional rounds with tool-using, reasoning agents
        6. Returns formatted debate with all rounds

        **Minimum 2 authors required for a debate.**
        """
        start_time = time.time()

        try:
            # Create Query object
            query = Query(
                text=request.text,
                specified_authors=request.specified_authors,
                max_authors=request.max_authors,
                min_authors=request.min_authors,
                relevance_threshold=request.relevance_threshold
            )

            # Get services
            semantic_router = services["semantic_router"]
            rag_pipeline = services["rag_pipeline"]
            agentic_debate_orchestrator = services["agentic_debate_orchestrator"]
            authors_dict = services["authors"]

            # Step 1: Select authors
            logger.info(f"Selecting authors for agentic debate: {query.text[:50]}...")
            selection_result = semantic_router.select_authors(query)

            if not selection_result.selected_authors:
                raise HTTPException(
                    status_code=400,
                    detail="No relevant authors found for query"
                )

            if len(selection_result.selected_authors) < 2:
                raise HTTPException(
                    status_code=400,
                    detail="Debate requires at least 2 authors"
                )

            logger.info(
                f"Selected {len(selection_result.selected_authors)} authors: "
                f"{', '.join(selection_result.selected_authors)}"
            )

            # Step 2: Get author objects
            selected_author_objs = [
                authors_dict[author_id]
                for author_id in selection_result.selected_authors
                if author_id in authors_dict
            ]

            if not selected_author_objs:
                raise HTTPException(
                    status_code=500,
                    detail="Selected authors not found in author database"
                )

            # Step 3: Generate initial responses concurrently
            logger.info("Generating initial responses from authors...")
            initial_responses = await rag_pipeline.generate_responses_concurrent(
                query=query,
                authors=selected_author_objs,
                query_embedding=selection_result.query_vector
            )

            if not initial_responses:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate any responses"
                )

            # Step 4: Orchestrate agentic debate
            logger.info(f"Orchestrating {request.num_rounds}-round agentic debate...")
            debate_response = await agentic_debate_orchestrator.orchestrate_debate(
                query=query,
                authors=selected_author_objs,
                initial_responses=initial_responses,
                query_embedding=selection_result.query_vector,
                selection_method=selection_result.selection_method,
                num_rounds=request.num_rounds,
                use_tools=True
            )

            # Step 5: Format and return
            return DebateResponseSchema(
                query_text=debate_response.query.text,
                rounds=[
                    DebateRoundSchema(
                        round_number=round_obj.round_number,
                        round_type=round_obj.round_type,
                        author_responses=[
                            AuthorResponseSchema(
                                author_id=resp.author_id,
                                author_name=resp.author_name,
                                response_text=resp.response_text,
                                relevance_score=resp.relevance_score,
                                retrieved_chunks=resp.retrieved_chunks,
                                generation_time_ms=resp.generation_time_ms
                            )
                            for resp in round_obj.author_responses
                        ]
                    )
                    for round_obj in debate_response.rounds
                ],
                total_time_ms=debate_response.total_time_ms,
                selection_method=debate_response.selection_method,
                author_count=debate_response.author_count,
                round_count=debate_response.round_count
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing agentic debate: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

    @router.post("/query/debate", response_model=DebateResponseSchema)
    async def query_debate(request: DebateRequest):
        """
        Start a multi-round debate between authors.

        This endpoint:
        1. Accepts a user query and debate parameters
        2. Selects relevant authors (automatically or from specified list)
        3. Generates initial responses from each author
        4. Conducts additional rounds where authors respond to each other
        5. Returns formatted debate with all rounds

        **Minimum 2 authors required for a debate.**
        """
        start_time = time.time()

        try:
            # Create Query object
            query = Query(
                text=request.text,
                specified_authors=request.specified_authors,
                max_authors=request.max_authors,
                min_authors=request.min_authors,
                relevance_threshold=request.relevance_threshold
            )

            # Get services
            semantic_router = services["semantic_router"]
            rag_pipeline = services["rag_pipeline"]
            debate_orchestrator = services["debate_orchestrator"]
            authors_dict = services["authors"]

            # Step 1: Select authors
            logger.info(f"Selecting authors for debate: {query.text[:50]}...")
            selection_result = semantic_router.select_authors(query)

            if not selection_result.selected_authors:
                raise HTTPException(
                    status_code=400,
                    detail="No relevant authors found for query"
                )

            if len(selection_result.selected_authors) < 2:
                raise HTTPException(
                    status_code=400,
                    detail="Debate requires at least 2 authors"
                )

            logger.info(
                f"Selected {len(selection_result.selected_authors)} authors: "
                f"{', '.join(selection_result.selected_authors)}"
            )

            # Step 2: Get author objects
            selected_author_objs = [
                authors_dict[author_id]
                for author_id in selection_result.selected_authors
                if author_id in authors_dict
            ]

            if not selected_author_objs:
                raise HTTPException(
                    status_code=500,
                    detail="Selected authors not found in author database"
                )

            # Step 3: Generate initial responses concurrently
            logger.info("Generating initial responses from authors...")
            initial_responses = await rag_pipeline.generate_responses_concurrent(
                query=query,
                authors=selected_author_objs,
                query_embedding=selection_result.query_vector
            )

            if not initial_responses:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate any responses"
                )

            # Step 4: Orchestrate debate
            logger.info(f"Orchestrating {request.num_rounds}-round debate...")
            debate_response = await debate_orchestrator.orchestrate_debate(
                query=query,
                authors=selected_author_objs,
                initial_responses=initial_responses,
                query_embedding=selection_result.query_vector,
                selection_method=selection_result.selection_method,
                num_rounds=request.num_rounds
            )

            # Step 5: Format and return
            return DebateResponseSchema(
                query_text=debate_response.query.text,
                rounds=[
                    DebateRoundSchema(
                        round_number=round_obj.round_number,
                        round_type=round_obj.round_type,
                        author_responses=[
                            AuthorResponseSchema(
                                author_id=resp.author_id,
                                author_name=resp.author_name,
                                response_text=resp.response_text,
                                relevance_score=resp.relevance_score,
                                retrieved_chunks=resp.retrieved_chunks,
                                generation_time_ms=resp.generation_time_ms
                            )
                            for resp in round_obj.author_responses
                        ]
                    )
                    for round_obj in debate_response.rounds
                ],
                total_time_ms=debate_response.total_time_ms,
                selection_method=debate_response.selection_method,
                author_count=debate_response.author_count,
                round_count=debate_response.round_count
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing debate: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

    @router.get("/authors", response_model=AuthorListResponse)
    async def list_authors():
        """
        List all available authors.

        Returns author profiles with their expertise domains and basic info.
        """
        try:
            authors_dict = services["authors"]

            authors_list = [
                {
                    "id": author.id,
                    "name": author.name,
                    "expertise_domains": author.expertise_domains,
                    "bio": author.bio,
                    "major_works": author.works
                }
                for author in authors_dict.values()
            ]

            return AuthorListResponse(
                authors=authors_list,
                total=len(authors_list)
            )

        except Exception as e:
            logger.error(f"Error listing authors: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve authors"
            )

    @router.get("/authors/{author_id}")
    async def get_author(author_id: str):
        """
        Get detailed information about a specific author.

        Args:
            author_id: Author identifier (e.g., 'marx', 'whitman', 'baudelaire')
        """
        try:
            authors_dict = services["authors"]

            if author_id not in authors_dict:
                raise HTTPException(
                    status_code=404,
                    detail=f"Author not found: {author_id}"
                )

            author = authors_dict[author_id]

            return {
                "id": author.id,
                "name": author.name,
                "expertise_domains": author.expertise_domains,
                "voice_characteristics": {
                    "tone": author.voice_characteristics.tone,
                    "vocabulary": author.voice_characteristics.vocabulary,
                    "perspective": author.voice_characteristics.perspective,
                    "style_notes": author.voice_characteristics.style_notes
                },
                "bio": author.bio,
                "major_works": author.works
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving author: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve author"
            )

    @router.get("/rankings")
    async def get_author_rankings(query: str):
        """
        Get all authors ranked by relevance to a query.

        Useful for understanding how the semantic router evaluates authors
        for a given query.

        Args:
            query: The query text to rank authors against
        """
        try:
            semantic_router = services["semantic_router"]

            query_obj = Query(text=query)
            rankings = semantic_router.get_author_rankings(query_obj)

            return {
                "query": query,
                "rankings": [
                    {
                        "author_id": author_id,
                        "similarity_score": score
                    }
                    for author_id, score in rankings
                ]
            }

        except Exception as e:
            logger.error(f"Error getting rankings: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get author rankings"
            )

    @router.post("/query/debate/agentic/stream")
    async def query_agentic_debate_stream(request: DebateRequest):
        """
        Stream agentic debate responses using Server-Sent Events.

        Returns responses incrementally as each round and author completes,
        providing a better user experience for multi-round debates.
        """
        async def generate():
            try:
                # Create Query object
                query = Query(
                    text=request.text,
                    specified_authors=request.specified_authors,
                    max_authors=request.max_authors,
                    min_authors=request.min_authors,
                    relevance_threshold=request.relevance_threshold
                )

                # Get services
                semantic_router = services["semantic_router"]
                rag_pipeline = services["rag_pipeline"]
                authors_dict = services["authors"]
                llm_client = services["llm_client"]

                # Step 1: Select authors
                logger.info(f"Selecting authors for streaming agentic debate: {query.text[:50]}...")
                selection_result = semantic_router.select_authors(query)

                if not selection_result.selected_authors:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'No relevant authors found'})}\n\n"
                    return

                if len(selection_result.selected_authors) < 2:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Debate requires at least 2 authors'})}\n\n"
                    return

                # Get author objects
                selected_author_objs = [
                    authors_dict[author_id]
                    for author_id in selection_result.selected_authors
                    if author_id in authors_dict
                ]

                # Send selected authors
                yield f"data: {json.dumps({'type': 'authors', 'authors': [{'id': a.id, 'name': a.name} for a in selected_author_objs]})}\n\n"

                # Step 2: Generate initial responses with token streaming
                logger.info("Generating initial responses...")
                yield f"data: {json.dumps({'type': 'round_start', 'round_number': 1, 'round_type': 'initial'})}\n\n"

                initial_responses = []
                for author in selected_author_objs:
                    # Signal author start
                    yield f"data: {json.dumps({'type': 'author_start', 'round_number': 1, 'author_id': author.id, 'author_name': author.name})}\n\n"

                    # Generate with token streaming
                    import time
                    start_time = time.time()

                    # Get chunks
                    chunks_with_scores = await asyncio.get_event_loop().run_in_executor(
                        None,
                        rag_pipeline.vector_db.search_chunks,
                        selection_result.query_vector,
                        author.id,
                        rag_pipeline.top_k_chunks
                    )

                    retrieved_chunks = [
                        {"id": chunk.id, "metadata": chunk.metadata}
                        for chunk, _ in chunks_with_scores
                    ]

                    # Stream tokens
                    full_text = ""
                    for token in llm_client.generate_streaming(
                        author.system_prompt,
                        query.text,
                        rag_pipeline.max_response_tokens,
                        rag_pipeline.temperature
                    ):
                        full_text += token
                        yield f"data: {json.dumps({'type': 'token', 'round_number': 1, 'author_id': author.id, 'author_name': author.name, 'token': token})}\n\n"

                    elapsed_ms = (time.time() - start_time) * 1000

                    # Compute relevance
                    similarity = sum(
                        c.metadata.get('similarity', 0) for c, _ in chunks_with_scores
                    ) / len(chunks_with_scores) if chunks_with_scores else 0

                    # Signal complete
                    yield f"data: {json.dumps({'type': 'response_complete', 'round_number': 1, 'author_id': author.id, 'author_name': author.name, 'response_text': full_text, 'relevance_score': similarity, 'retrieved_chunks': retrieved_chunks})}\n\n"

                    # Store for next round
                    from src.data.models import AuthorResponse
                    initial_responses.append(AuthorResponse(
                        author_id=author.id,
                        author_name=author.name,
                        response_text=full_text,
                        relevance_score=similarity,
                        retrieved_chunks=retrieved_chunks,
                        generation_time_ms=elapsed_ms
                    ))

                # Step 3: Orchestrate additional rounds with streaming
                from src.processing.agentic_debate_orchestrator import (
                    AgenticDebateOrchestrator,
                    SharedDebateKnowledgeBase,
                    DebateAgent
                )

                knowledge_base = SharedDebateKnowledgeBase()

                # Record initial responses
                for response in initial_responses:
                    await knowledge_base.record_response(
                        round_number=1,
                        author_id=response.author_id,
                        author_name=response.author_name,
                        response_text=response.response_text,
                        tool_uses=0,
                        reasoning_steps=0
                    )

                # Create debate agents
                agents = {
                    author.id: DebateAgent(
                        author=author,
                        rag_pipeline=rag_pipeline,
                        llm_client=llm_client,
                        knowledge_base=knowledge_base,
                        max_response_tokens=400,
                        temperature=0.7
                    )
                    for author in selected_author_objs
                }

                # Additional rounds
                num_rounds = request.num_rounds
                previous_responses = initial_responses

                for round_num in range(2, num_rounds + 1):
                    round_type = "rebuttal" if round_num == 2 else "response"
                    yield f"data: {json.dumps({'type': 'round_start', 'round_number': round_num, 'round_type': round_type})}\n\n"

                    logger.info(f"Generating agentic round {round_num}...")

                    # Generate responses for this round
                    round_responses = []
                    for agent in agents.values():
                        # Get other authors' responses
                        other_responses = [
                            resp for resp in previous_responses
                            if resp.author_id != agent.author.id
                        ]

                        # Signal author start
                        yield f"data: {json.dumps({'type': 'author_start', 'round_number': round_num, 'author_id': agent.author.id, 'author_name': agent.author.name})}\n\n"

                        # Generate response with streaming
                        response = await generate_streaming_response(
                            agent=agent,
                            query=query,
                            other_responses=other_responses,
                            round_number=round_num,
                            yield_func=lambda token: f"data: {json.dumps({'type': 'token', 'round_number': round_num, 'author_id': agent.author.id, 'token': token})}\n\n"
                        )

                        # Yield each token as it's generated
                        full_text = ""
                        async for token in response['stream']:
                            full_text += token
                            yield f"data: {json.dumps({'type': 'token', 'round_number': round_num, 'author_id': agent.author.id, 'author_name': agent.author.name, 'token': token})}\n\n"

                        # Signal author complete with final response
                        yield f"data: {json.dumps({'type': 'response_complete', 'round_number': round_num, 'author_id': agent.author.id, 'author_name': agent.author.name, 'response_text': full_text, 'relevance_score': response['relevance_score'], 'retrieved_chunks': response['retrieved_chunks']})}\n\n"

                        # Store for next round
                        from src.data.models import AuthorResponse
                        author_response = AuthorResponse(
                            author_id=agent.author.id,
                            author_name=agent.author.name,
                            response_text=full_text,
                            relevance_score=1.0,
                            retrieved_chunks=response['retrieved_chunks'],
                            generation_time_ms=response['generation_time_ms']
                        )
                        round_responses.append(author_response)

                    # Update previous responses for next round
                    previous_responses = round_responses

                # Send completion signal
                stats = await knowledge_base.get_stats()
                yield f"data: {json.dumps({'type': 'done', 'stats': stats})}\n\n"

            except Exception as e:
                logger.error(f"Error in streaming agentic debate: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    @router.post("/query/stream")
    async def query_stream(request: QueryRequest):
        """
        Stream author responses using Server-Sent Events.

        Returns responses incrementally as each author completes,
        providing a better user experience.
        """
        async def generate():
            try:
                # Create Query object
                query = Query(
                    text=request.text,
                    specified_authors=request.specified_authors,
                    max_authors=request.max_authors,
                    min_authors=request.min_authors,
                    relevance_threshold=request.relevance_threshold
                )

                # Get services
                semantic_router = services["semantic_router"]
                rag_pipeline = services["rag_pipeline"]
                authors_dict = services["authors"]

                # Step 1: Select authors
                logger.info(f"Selecting authors for query (streaming): {query.text[:50]}...")
                selection_result = semantic_router.select_authors(query)

                if not selection_result.selected_authors:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'No relevant authors found'})}\n\n"
                    return

                # Send selected authors
                selected_author_objs = [
                    authors_dict[author_id]
                    for author_id in selection_result.selected_authors
                    if author_id in authors_dict
                ]

                yield f"data: {json.dumps({'type': 'authors', 'authors': [{'id': a.id, 'name': a.name} for a in selected_author_objs]})}\n\n"

                # Step 2: Generate responses concurrently and stream
                tasks = []
                for author in selected_author_objs:
                    task = rag_pipeline.generate_response(
                        author=author,
                        query=query,
                        query_embedding=selection_result.query_vector
                    )
                    tasks.append((author, task))

                # Stream responses as they complete
                for coro in asyncio.as_completed([task for _, task in tasks]):
                    response = await coro

                    # Find which author this response is for
                    author_name = response.author_name

                    yield f"data: {json.dumps({'type': 'response', 'author_id': response.author_id, 'author_name': author_name, 'response': response.response_text, 'relevance': response.relevance_score})}\n\n"

                # Send completion signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                logger.error(f"Error in streaming: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    return router
