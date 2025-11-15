"""
Pydantic schemas for API requests and responses.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request schema for querying the debate panel."""
    text: str = Field(..., min_length=1, max_length=5000, description="The user's question")
    specified_authors: Optional[List[str]] = Field(
        None,
        description="Specific author IDs to query (None for automatic selection)"
    )
    max_authors: int = Field(5, ge=2, le=10, description="Maximum number of authors")
    min_authors: int = Field(2, ge=1, le=5, description="Minimum number of authors")
    relevance_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity for author selection"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "What is the meaning of life?",
                "max_authors": 3,
                "min_authors": 2,
                "relevance_threshold": 0.7
            }
        }


class AuthorResponseSchema(BaseModel):
    """Schema for a single author's response."""
    author_id: str
    author_name: str
    response_text: str
    relevance_score: float
    retrieved_chunks: List[Dict[str, Any]] = []
    generation_time_ms: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "author_id": "marx",
                "author_name": "Karl Marx",
                "response_text": "The meaning of life lies in the material conditions...",
                "relevance_score": 0.85,
                "generation_time_ms": 1234.5
            }
        }


class DebatePanelResponseSchema(BaseModel):
    """Schema for the complete debate panel response."""
    query_text: str
    authors: List[AuthorResponseSchema]
    total_time_ms: float
    selection_method: str
    author_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "query_text": "What is the meaning of life?",
                "authors": [
                    {
                        "author_id": "marx",
                        "author_name": "Karl Marx",
                        "response_text": "The meaning lies in the material conditions...",
                        "relevance_score": 0.85,
                        "generation_time_ms": 1234.5
                    }
                ],
                "total_time_ms": 3500.0,
                "selection_method": "threshold",
                "author_count": 3
            }
        }


class AuthorListResponse(BaseModel):
    """Schema for listing available authors."""
    authors: List[dict]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "authors": [
                    {
                        "id": "marx",
                        "name": "Karl Marx",
                        "expertise_domains": ["political_economy", "capitalism"]
                    }
                ],
                "total": 3
            }
        }


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    components: dict

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "components": {
                    "vector_db": "connected",
                    "llm": "connected",
                    "embeddings": "connected"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid request",
                "detail": "Query text cannot be empty",
                "code": "VALIDATION_ERROR"
            }
        }


class DebateRequest(BaseModel):
    """Request schema for debate endpoint."""
    text: str = Field(..., min_length=1, max_length=5000, description="The user's question")
    specified_authors: Optional[List[str]] = Field(
        None,
        description="Specific author IDs to query (None for automatic selection)"
    )
    max_authors: int = Field(5, ge=2, le=10, description="Maximum number of authors")
    min_authors: int = Field(2, ge=2, le=5, description="Minimum number of authors (must be >= 2)")
    relevance_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity for author selection"
    )
    num_rounds: int = Field(
        2, ge=1, le=5, description="Number of debate rounds (1 = initial only, 2+ = with rebuttals)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "What is the meaning of life?",
                "max_authors": 3,
                "min_authors": 2,
                "relevance_threshold": 0.7,
                "num_rounds": 2
            }
        }


class DebateRoundSchema(BaseModel):
    """Schema for a single debate round."""
    round_number: int
    round_type: str
    author_responses: List[AuthorResponseSchema]

    class Config:
        json_schema_extra = {
            "example": {
                "round_number": 1,
                "round_type": "initial",
                "author_responses": [
                    {
                        "author_id": "marx",
                        "author_name": "Karl Marx",
                        "response_text": "The meaning lies in the material conditions...",
                        "relevance_score": 0.85,
                        "generation_time_ms": 1234.5
                    }
                ]
            }
        }


class DebateResponseSchema(BaseModel):
    """Schema for complete debate response."""
    query_text: str
    rounds: List[DebateRoundSchema]
    total_time_ms: float
    selection_method: str
    author_count: int
    round_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "query_text": "What is the meaning of life?",
                "rounds": [
                    {
                        "round_number": 1,
                        "round_type": "initial",
                        "author_responses": [
                            {
                                "author_id": "marx",
                                "author_name": "Karl Marx",
                                "response_text": "The meaning lies in the material conditions...",
                                "relevance_score": 0.85,
                                "generation_time_ms": 1234.5
                            }
                        ]
                    }
                ],
                "total_time_ms": 7500.0,
                "selection_method": "threshold",
                "author_count": 3,
                "round_count": 2
            }
        }
