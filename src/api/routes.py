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
            logger.error(f"Error processing query: {e}", exc_info=True)
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
