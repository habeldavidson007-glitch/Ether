"""
Dynamic Query Router for Ether AI
Routes queries to appropriate handlers based on type and complexity.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
import re


class QueryType(Enum):
    """Types of queries that can be routed."""
    CODING_FIX = "coding_fix"
    CODING_EXPLAIN = "coding_explain"
    GODOT_SPECIFIC = "godot_specific"
    GENERAL_QUESTION = "general_question"
    MATH_LOGIC = "math_logic"
    COMPARISON = "comparison"
    EXPLANATION = "explanation"
    UNKNOWN = "unknown"


@dataclass
class RoutingDecision:
    """Result of query routing."""
    query_type: QueryType
    confidence: float
    recommended_handler: str
    reasoning: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class QueryRouter:
    """
    Dynamic query router that classifies and routes queries
    to the most appropriate handler.
    """

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.type_patterns: Dict[QueryType, List[str]] = self._init_patterns()
        self.default_handler: Optional[str] = None

    def _init_patterns(self) -> Dict[QueryType, List[str]]:
        """Initialize keyword patterns for query type detection."""
        return {
            QueryType.CODING_FIX: [
                r'\b(error|bug|issue|problem|broken|fail|crash)\b',
                r'\b(fix|repair|correct|resolve|debug)\b',
                r'\b(traceback|exception|assertion)\b',
                r':\s*error',
                r'not\s+defined',
                r'invalid\s+syntax'
            ],
            QueryType.CODING_EXPLAIN: [
                r'\b(how\s+to|how\s+do\s+i|how\s+can\s+i)\b',
                r'\b(implement|create|make|build|write)\b',
                r'\b(code|function|method|script|class)\b',
                r'\b(example|snippet|template)\b'
            ],
            QueryType.GODOT_SPECIFIC: [
                r'\bgodot\b',
                r'\bgdscript\b',
                r'\b(node|scene|signal|slot|inspector)\b',
                r'\b(kinematic|rigid|area|collision)\b',
                r'\b(shader|material|texture|mesh)\b',
                r'\b(tween|animation|state_machine)\b',
                r'res://',
                r'func\s+_ready',
                r'extends\s+'
            ],
            QueryType.MATH_LOGIC: [
                r'\b(calculate|compute|solve|evaluate)\b',
                r'\b(math|mathematics|algebra|calculus|geometry)\b',
                r'\b(equation|formula|theorem|proof)\b',
                r'\b(logic|boolean|truth|false)\b',
                r'[+\-*/]=',
                r'\d+\s*[+\-*/]\s*\d+'
            ],
            QueryType.COMPARISON: [
                r'\b(compare|comparison|difference)\b',
                r'\b(vs|versus|rather\s+than|instead\s+of)\b',
                r'\b(better|worse|faster|slower|more\s+efficient)\b',
                r'\b(pros|cons|advantage|disadvantage)\b'
            ],
            QueryType.EXPLANATION: [
                r'\b(explain|describe|define|clarify)\b',
                r'\b(what\s+is|what\s+are|who\s+is|when\s+to)\b',
                r'\b(how\s+does|why\s+does|why\s+is)\b',
                r'\b(concept|meaning|purpose|reason)\b'
            ],
            QueryType.GENERAL_QUESTION: [
                r'\?$',
                r'\b(can\s+you|could\s+you|will\s+you)\b',
                r'\b(tell\s+me|show\s+me|give\s+me)\b'
            ]
        }

    def register_handler(self, handler_name: str, handler: Callable):
        """Register a handler function."""
        self.handlers[handler_name] = handler

    def set_default_handler(self, handler_name: str):
        """Set the default handler for unknown query types."""
        self.default_handler = handler_name

    def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Analyze a query and determine the best routing.
        
        Args:
            query: The user's query text
            context: Additional context about the user or session
            
        Returns:
            RoutingDecision with type, confidence, and recommended handler
        """
        # Score each query type
        scores: Dict[QueryType, float] = {}
        matched_patterns: Dict[QueryType, List[str]] = {}
        
        for query_type, patterns in self.type_patterns.items():
            score = 0.0
            matches = []
            
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    score += 1.0
                    matches.append(pattern)
            
            # Apply boosts for strong indicators
            if query_type == QueryType.GODOT_SPECIFIC and 'godot' in query.lower():
                score *= 1.5
            if query_type == QueryType.CODING_FIX and any(
                kw in query.lower() for kw in ['error', 'exception', 'traceback']
            ):
                score *= 1.3
            
            scores[query_type] = score
            matched_patterns[query_type] = matches
        
        # Find the best matching type
        best_type = QueryType.UNKNOWN
        best_score = 0.0
        
        for query_type, score in scores.items():
            if score > best_score:
                best_score = score
                best_type = query_type
        
        # Calculate confidence (normalize to 0-1 range)
        total_patterns = sum(len(p) for p in self.type_patterns.values())
        confidence = min(1.0, best_score / max(1, total_patterns * 0.1))
        
        # Determine recommended handler
        recommended_handler = self._get_recommended_handler(best_type, query)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(best_type, matched_patterns.get(best_type, []), scores)
        
        return RoutingDecision(
            query_type=best_type,
            confidence=round(confidence, 2),
            recommended_handler=recommended_handler,
            reasoning=reasoning,
            metadata={
                "all_scores": {k.value: round(v, 2) for k, v in scores.items()},
                "matched_patterns_count": len(matched_patterns.get(best_type, []))
            }
        )

    def _get_recommended_handler(self, query_type: QueryType, query: str) -> str:
        """Get the recommended handler name for a query type."""
        handler_mapping = {
            QueryType.CODING_FIX: "code_fixer",
            QueryType.CODING_EXPLAIN: "code_explainer",
            QueryType.GODOT_SPECIFIC: "godot_specialist",
            QueryType.MATH_LOGIC: "math_solver",
            QueryType.COMPARISON: "comparator",
            QueryType.EXPLANATION: "explainer",
            QueryType.GENERAL_QUESTION: "general_assistant"
        }
        
        base_handler = handler_mapping.get(query_type, "general_assistant")
        
        # Check if we have a registered handler
        if base_handler in self.handlers:
            return base_handler
        
        # Fall back to available handlers
        if self.handlers:
            return list(self.handlers.keys())[0]
        
        return self.default_handler or "general_assistant"

    def _generate_reasoning(
        self,
        query_type: QueryType,
        matched_patterns: List[str],
        all_scores: Dict[QueryType, float]
    ) -> str:
        """Generate human-readable reasoning for the routing decision."""
        if query_type == QueryType.UNKNOWN:
            return "No clear pattern matched; using default handling."
        
        pattern_count = len(matched_patterns)
        second_best_score = sorted(all_scores.values(), reverse=True)[1] if len(all_scores) > 1 else 0
        
        reasoning_parts = [
            f"Detected {query_type.value} query",
            f"matched {pattern_count} pattern(s)"
        ]
        
        if all_scores[query_type] > second_best_score * 2:
            reasoning_parts.append("with high confidence")
        elif all_scores[query_type] > second_best_score:
            reasoning_parts.append("with moderate confidence")
        else:
            reasoning_parts.append("but other types were also possible")
        
        return "; ".join(reasoning_parts) + "."

    def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Route and execute a query automatically.
        
        Args:
            query: The user's query
            context: Additional context
            
        Returns:
            Result from the executed handler
        """
        decision = self.route(query, context)
        
        handler_name = decision.recommended_handler
        
        if handler_name not in self.handlers:
            if self.default_handler and self.default_handler in self.handlers:
                handler_name = self.default_handler
            else:
                raise ValueError(f"No handler available for query type: {decision.query_type}")
        
        handler = self.handlers[handler_name]
        return handler(query, context=context, routing_decision=decision)

    def get_statistics(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "registered_handlers": list(self.handlers.keys()),
            "default_handler": self.default_handler,
            "query_types": len(self.type_patterns),
            "total_patterns": sum(len(p) for p in self.type_patterns.values())
        }
