"""
Data models for the Virtual Debate Panel application.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class AuthorExpertise(str, Enum):
    """Enumeration of author expertise domains."""
    POLITICAL_ECONOMY = "political_economy"
    PHILOSOPHY = "philosophy"
    POETRY = "poetry"
    PSYCHOLOGY = "psychology"
    SELF_HELP = "self_help"
    LITERATURE = "literature"
    HISTORY = "history"
    SCIENCE = "science"


class VoiceCharacteristics(BaseModel):
    """Characteristics defining an author's unique voice."""
    tone: str = Field(..., description="Overall tone (e.g., analytical, poetic, conversational)")
    vocabulary: str = Field(..., description="Key vocabulary characteristics")
    perspective: str = Field(..., description="Philosophical or analytical perspective")
    style_notes: Optional[str] = Field(None, description="Additional style guidance")


class Author(BaseModel):
    """Representation of an author in the system."""
    id: str = Field(..., description="Unique identifier (e.g., 'marx', 'whitman')")
    name: str = Field(..., description="Full name (e.g., 'Karl Marx')")
    expertise_domains: List[str] = Field(..., description="List of expertise areas")
    voice_characteristics: VoiceCharacteristics
    system_prompt: str = Field(..., description="System prompt for LLM")
    expertise_vector: Optional[List[float]] = Field(
        None, description="Embedding vector for expertise matching"
    )
    bio: Optional[str] = Field(None, description="Brief biographical information")
    works: Optional[List[str]] = Field(None, description="List of major works")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "marx",
                "name": "Karl Marx",
                "expertise_domains": ["political_economy", "capitalism", "class_struggle"],
                "voice_characteristics": {
                    "tone": "analytical, critical, revolutionary",
                    "vocabulary": "dialectical, materialist, proletarian",
                    "perspective": "class-based economic analysis"
                },
                "system_prompt": "You are Karl Marx...",
                "bio": "19th-century philosopher and economist",
                "works": ["Capital", "The Communist Manifesto"]
            }
        }


class TextChunk(BaseModel):
    """A chunk of text from an author's work."""
    id: str = Field(..., description="Unique chunk identifier")
    author_id: str = Field(..., description="Author who wrote this text")
    text: str = Field(..., description="The actual text content")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (book, page, chapter, etc.)"
    )

    @validator('text')
    def text_not_empty(cls, v: str) -> str:
        """Ensure text is not empty."""
        if not v or not v.strip():
            raise ValueError("Text content cannot be empty")
        return v


class Query(BaseModel):
    """User query to the Virtual Debate Panel."""
    text: str = Field(..., description="The user's question or prompt")
    specified_authors: Optional[List[str]] = Field(
        None,
        description="Specific author IDs to query (None for automatic selection)"
    )
    max_authors: int = Field(5, ge=2, le=10, description="Maximum number of authors")
    min_authors: int = Field(2, ge=1, le=5, description="Minimum number of authors")
    relevance_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity for author selection"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @validator('text')
    def text_not_empty(cls, v: str) -> str:
        """Ensure query text is not empty."""
        if not v or not v.strip():
            raise ValueError("Query text cannot be empty")
        return v

    @validator('min_authors')
    def min_lte_max(cls, v: int, values: Dict[str, Any]) -> int:
        """Ensure min_authors <= max_authors."""
        if 'max_authors' in values and v > values['max_authors']:
            raise ValueError("min_authors must be <= max_authors")
        return v


class AuthorResponse(BaseModel):
    """Response from a single author."""
    author_id: str = Field(..., description="Author who generated this response")
    author_name: str = Field(..., description="Full name of the author")
    response_text: str = Field(..., description="The generated response (max 3 paragraphs)")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Semantic similarity to query"
    )
    retrieved_chunks: List[str] = Field(
        default_factory=list, description="IDs of chunks used for context"
    )
    generation_time_ms: Optional[float] = Field(
        None, description="Time taken to generate response"
    )

    @validator('response_text')
    def validate_paragraph_count(cls, v: str) -> str:
        """Warn if response exceeds 3 paragraphs (soft validation)."""
        paragraphs = [p for p in v.split('\n\n') if p.strip()]
        if len(paragraphs) > 3:
            # Note: This is informational; we don't raise an error
            pass
        return v


class DebatePanelResponse(BaseModel):
    """Aggregated response from multiple authors."""
    query: Query = Field(..., description="Original user query")
    authors: List[AuthorResponse] = Field(..., description="Responses from each author")
    total_time_ms: float = Field(..., description="Total time for entire operation")
    selection_method: str = Field(
        ..., description="How authors were selected (semantic, specified, fallback)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def author_count(self) -> int:
        """Number of authors in the panel."""
        return len(self.authors)

    def get_author_response(self, author_id: str) -> Optional[AuthorResponse]:
        """Get response from a specific author."""
        return next((a for a in self.authors if a.author_id == author_id), None)


class AuthorSelectionResult(BaseModel):
    """Result of the semantic routing process."""
    selected_authors: List[str] = Field(..., description="IDs of selected authors")
    similarity_scores: Dict[str, float] = Field(
        ..., description="Similarity score for each author"
    )
    selection_method: str = Field(
        ..., description="Method used (threshold, top_k, fallback)"
    )
    query_vector: List[float] = Field(..., description="Embedded query vector")
    threshold_used: float = Field(..., description="Relevance threshold applied")
