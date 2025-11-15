"""
FastAPI application for the Virtual Debate Panel.
"""
import time
from contextlib import asynccontextmanager
from typing import Dict

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config.settings import settings
from src.data import get_embedding_provider, get_vector_db
from src.data.models import Author, VoiceCharacteristics
from src.processing import PromptManager, RAGPipeline, get_llm_client
from src.processing.debate_orchestrator import DebateOrchestrator
from src.processing.agentic_debate_orchestrator import AgenticDebateOrchestrator
from src.routing import ResponseAggregator, SemanticRouter

from .routes import create_router

# Global service instances
services: Dict = {}


def load_authors_from_config() -> Dict[str, Author]:
    """Load author profiles from YAML config files."""
    authors = {}
    author_files = ["marx", "whitman", "baudelaire"]

    for author_id in author_files:
        try:
            with open(f"config/authors/{author_id}.yaml", "r") as f:
                data = yaml.safe_load(f)

            authors[author_id] = Author(
                id=author_id,
                name=data["name"],
                expertise_domains=data["expertise_domains"],
                voice_characteristics=VoiceCharacteristics(**data["voice_characteristics"]),
                system_prompt=data["system_prompt"],
                bio=data.get("bio"),
                works=data.get("major_works", [])
            )
            logger.info(f"Loaded author: {data['name']}")
        except Exception as e:
            logger.error(f"Failed to load author {author_id}: {e}")

    return authors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initializes and cleans up services."""
    logger.info("Starting Virtual Debate Panel API...")

    try:
        # Initialize vector database
        logger.info(f"Initializing vector database: {settings.vector_db}")
        vector_db = get_vector_db(**settings.get_vector_db_config())
        vector_db.initialize()
        services["vector_db"] = vector_db

        # Initialize embedding provider
        logger.info(f"Initializing embedding provider: {settings.llm_provider}")
        embedding_provider = get_embedding_provider(**settings.get_embedding_config())
        services["embedding_provider"] = embedding_provider

        # Initialize LLM client
        logger.info(f"Initializing LLM client: {settings.llm_provider}")
        llm_client = get_llm_client(**settings.get_llm_config())
        services["llm_client"] = llm_client

        # Initialize prompt manager
        prompt_manager = PromptManager()
        services["prompt_manager"] = prompt_manager

        # Load author profiles
        logger.info("Loading author profiles...")
        authors = load_authors_from_config()
        services["authors"] = authors
        logger.info(f"Loaded {len(authors)} author profiles")

        # Initialize semantic router
        semantic_router = SemanticRouter(
            vector_db=vector_db,
            embedding_provider=embedding_provider,
            relevance_threshold=settings.relevance_threshold,
            min_authors=settings.min_authors,
            max_authors=settings.max_authors,
            fallback_to_top=settings.fallback_to_top_authors
        )
        services["semantic_router"] = semantic_router

        # Initialize RAG pipeline
        rag_pipeline = RAGPipeline(
            vector_db=vector_db,
            embedding_provider=embedding_provider,
            llm_client=llm_client,
            top_k_chunks=settings.top_k_chunks,
            max_response_tokens=settings.max_response_tokens,
            temperature=settings.llm_temperature
        )
        services["rag_pipeline"] = rag_pipeline

        # Initialize debate orchestrator
        debate_orchestrator = DebateOrchestrator(
            rag_pipeline=rag_pipeline,
            llm_client=llm_client,
            max_response_tokens=settings.max_response_tokens,
            temperature=settings.llm_temperature
        )
        services["debate_orchestrator"] = debate_orchestrator

        # Initialize agentic debate orchestrator
        agentic_debate_orchestrator = AgenticDebateOrchestrator(
            rag_pipeline=rag_pipeline,
            llm_client=llm_client,
            max_response_tokens=settings.max_response_tokens,
            temperature=settings.llm_temperature
        )
        services["agentic_debate_orchestrator"] = agentic_debate_orchestrator

        # Initialize response aggregator
        response_aggregator = ResponseAggregator()
        services["response_aggregator"] = response_aggregator

        logger.info("All services initialized successfully!")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield  # Application runs here

    # Cleanup
    logger.info("Shutting down Virtual Debate Panel API...")
    services.clear()


# Create FastAPI application
app = FastAPI(
    title="Virtual Debate Panel API",
    description="Multi-perspective chat application with RAG-based author responses",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
router = create_router(services)
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Virtual Debate Panel API",
        "version": "0.1.0",
        "description": "Multi-perspective chat application with RAG-based author responses",
        "endpoints": {
            "query": "/api/query",
            "debate": "/api/query/debate",
            "agentic_debate": "/api/query/debate/agentic",
            "authors": "/api/authors",
            "health": "/api/health",
            "docs": "/docs"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    status = {
        "status": "healthy",
        "version": "0.1.0",
        "components": {}
    }

    # Check vector database
    try:
        if "vector_db" in services:
            status["components"]["vector_db"] = "connected"
        else:
            status["components"]["vector_db"] = "not_initialized"
    except Exception as e:
        status["components"]["vector_db"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check LLM client
    try:
        if "llm_client" in services:
            status["components"]["llm"] = "connected"
        else:
            status["components"]["llm"] = "not_initialized"
    except Exception as e:
        status["components"]["llm"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check embedding provider
    try:
        if "embedding_provider" in services:
            status["components"]["embeddings"] = "connected"
        else:
            status["components"]["embeddings"] = "not_initialized"
    except Exception as e:
        status["components"]["embeddings"] = f"error: {str(e)}"
        status["status"] = "degraded"

    return status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
