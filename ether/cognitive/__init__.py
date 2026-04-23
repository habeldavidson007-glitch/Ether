"""
Cognitive Module for Ether AI
Provides semantic search, chain-of-thought reasoning, and dynamic routing.
"""

from .semantic_search import SemanticSearchEngine
from .reasoning import ChainOfThoughtReasoner
from .router import QueryRouter, QueryType

__all__ = [
    "SemanticSearchEngine",
    "ChainOfThoughtReasoner",
    "QueryRouter",
    "QueryType",
]
