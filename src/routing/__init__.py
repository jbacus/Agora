"""
Logic layer for the Virtual Debate Panel.
Handles semantic routing and response aggregation.
"""
from .response_aggregator import ResponseAggregator
from .semantic_router import SemanticRouter

__all__ = [
    "SemanticRouter",
    "ResponseAggregator",
]
