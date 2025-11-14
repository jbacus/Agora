"""
Processing layer for the Virtual Debate Panel.
Handles LLM integration and RAG pipeline.
"""
from .llm_client import (
    AnthropicClient,
    GeminiClient,
    LLMClient,
    OpenAIClient,
    get_llm_client,
)
from .prompts import (
    BAUDELAIRE_PROMPT,
    MARX_PROMPT,
    WHITMAN_PROMPT,
    PromptManager,
)
from .rag_pipeline import RAGPipeline

__all__ = [
    # LLM Clients
    "LLMClient",
    "GeminiClient",
    "OpenAIClient",
    "AnthropicClient",
    "get_llm_client",
    # RAG Pipeline
    "RAGPipeline",
    # Prompts
    "PromptManager",
    "MARX_PROMPT",
    "WHITMAN_PROMPT",
    "BAUDELAIRE_PROMPT",
]
