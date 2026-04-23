"""
Ether Consciousness Engine - Phase 10: The Great Unification
============================================================
A deterministic neuro-symbolic engine that unifies all fragmented modules
into a single autonomous agent with memory, reasoning, and tool execution.

Author: Ether Team
Version: 2.0.0
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

# ML Dependencies (optional, fallback to rules if missing)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ThoughtProcess:
    """Represents a single step in the consciousness reasoning chain."""
    step_id: int
    action: str
    reasoning: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConsciousState:
    """Current working memory and context of the agent."""
    query: str
    intent: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    thought_chain: List[ThoughtProcess] = field(default_factory=list)
    selected_tools: List[str] = field(default_factory=list)
    execution_results: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    is_safe: bool = True


class Hippocampus:
    """
    Unified Memory System
    Combines: AdaptiveMemory, Librarian, VectorStore, SecurityContext
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".ether" / "memory"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Unified semantic index
        self.semantic_index: Dict[str, List[float]] = {}
        self.short_term_memory: List[Dict] = []
        self.long_term_memory: List[Dict] = []
        
        logger.info(f"Hippocampus initialized at {self.storage_path}")
    
    def store(self, key: str, value: Any, memory_type: str = "short") -> None:
        """Store data in unified memory."""
        entry = {
            "key": key,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0
        }
        
        if memory_type == "short":
            self.short_term_memory.append(entry)
            if len(self.short_term_memory) > 100:  # Cap short-term memory
                self._consolidate_to_long_term()
        else:
            self.long_term_memory.append(entry)
            self._persist_to_disk(key, value)
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant memories using hybrid search."""
        results = []
        
        # 1. Recent context (Short-term memory)
        recent = [m for m in self.short_term_memory[-10:] if query.lower() in str(m.get("value", "")).lower()]
        results.extend(recent)
        
        # 2. Long-term memory
        long_term = [m for m in self.long_term_memory if query.lower() in str(m.get("value", "")).lower()]
        results.extend(long_term)
        
        # Deduplicate and rank
        seen = set()
        unique_results = []
        for r in results:
            key = json.dumps(r, sort_keys=True) if isinstance(r, dict) else str(r)
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        return unique_results[:top_k]
    
    def _consolidate_to_long_term(self):
        """Move important short-term memories to long-term."""
        if self.short_term_memory:
            oldest = self.short_term_memory.pop(0)
            if oldest.get("access_count", 0) > 2:
                self.long_term_memory.append(oldest)
    
    def _persist_to_disk(self, key: str, value: Any):
        """Persist critical memory to disk."""
        try:
            path = self.storage_path / f"{hashlib.md5(key.encode()).hexdigest()}.json"
            with open(path, 'w') as f:
                json.dump({"key": key, "value": value}, f)
        except Exception as e:
            logger.error(f"Failed to persist memory: {e}")
    
    def get_context_summary(self) -> str:
        """Generate a summary of current context for the LLM."""
        summary = []
        if self.short_term_memory:
            summary.append(f"Recent context: {len(self.short_term_memory)} items")
        if self.long_term_memory:
            summary.append(f"Long-term knowledge: {len(self.long_term_memory)} items")
        return "; ".join(summary)


class Cortex:
    """
    Deterministic Decision Engine
    Combines: Router, SemanticSearch, ReasoningEngine, IntentClassifier
    Uses ML + Rules for predictable decision making.
    """
    
    INTENT_PATTERNS = {
        "fix_code": [r"fix", r"error", r"bug", r"broken", r"not working"],
        "analyze": [r"analyze", r"check", r"scan", r"inspect", r"review"],
        "explain": [r"explain", r"what does", r"how does", r"why"],
        "optimize": [r"optimize", r"improve", r"speed up", r"refactor"],
        "generate": [r"create", r"generate", r"write", r"make"],
        "debug": [r"debug", r"trace", r"step through", r"breakpoint"],
        "general": [r"hello", r"help", r"question", r"tell me"]
    }
    
    def __init__(self):
        self.model: Optional[Pipeline] = None
        self.is_trained = False
        self.intent_history: List[str] = []
        
        if ML_AVAILABLE:
            self._initialize_ml_model()
        else:
            logger.warning("ML libraries not available. Falling back to rule-based classification.")
    
    def _initialize_ml_model(self):
        """Initialize lightweight ML pipeline for intent classification."""
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=500)),
            ('clf', LogisticRegression(max_iter=1000, multi_class='auto'))
        ])
    
    def train(self, samples: List[Tuple[str, str]]):
        """Train the intent classifier on provided samples."""
        if not ML_AVAILABLE or not self.model:
            return
        
        texts, labels = zip(*samples)
        self.model.fit(texts, labels)
        self.is_trained = True
        logger.info(f"Cortex trained on {len(samples)} samples")
    
    def classify_intent(self, query: str) -> Tuple[str, float]:
        """Determine intent using ML or fallback to rules."""
        query_lower = query.lower()
        
        # Try ML first if available and trained
        if ML_AVAILABLE and self.is_trained and self.model:
            try:
                prediction = self.model.predict([query])[0]
                proba = self.model.predict_proba([query])[0].max()
                return prediction, float(proba)
            except Exception:
                pass
        
        # Fallback to deterministic rule-based matching
        best_intent = "general"
        best_score = 0.0
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, query_lower))
            if score > best_score:
                best_score = score
                best_intent = intent
        
        confidence = min(best_score / 3.0, 1.0)  # Normalize
        return best_intent, confidence
    
    def reason(self, state: ConsciousState) -> ConsciousState:
        """Execute chain-of-thought reasoning."""
        # Step 1: Classify Intent
        intent, confidence = self.classify_intent(state.query)
        state.intent = intent
        state.confidence_score = confidence
        
        state.thought_chain.append(ThoughtProcess(
            step_id=1,
            action="classify_intent",
            reasoning=f"Detected intent '{intent}' with confidence {confidence:.2f}",
            confidence=confidence
        ))
        
        # Step 2: Select Tools based on intent
        tools = self._select_tools_for_intent(intent)
        state.selected_tools = tools
        
        state.thought_chain.append(ThoughtProcess(
            step_id=2,
            action="select_tools",
            reasoning=f"Selected tools: {', '.join(tools)} for intent '{intent}'",
            confidence=0.9
        ))
        
        # Step 3: Safety Check
        is_safe = self._safety_check(state)
        state.is_safe = is_safe
        
        state.thought_chain.append(ThoughtProcess(
            step_id=3,
            action="safety_check",
            reasoning=f"Safety validation: {'PASSED' if is_safe else 'FAILED'}",
            confidence=1.0 if is_safe else 0.0
        ))
        
        return state
    
    def _select_tools_for_intent(self, intent: str) -> List[str]:
        """Map intents to appropriate tools."""
        mapping = {
            "fix_code": ["code_fixer", "static_analyzer"],
            "analyze": ["static_analyzer", "dependency_graph"],
            "explain": ["static_analyzer"],
            "optimize": ["static_analyzer", "code_fixer"],
            "generate": ["code_fixer"],
            "debug": ["cascade_scanner", "static_analyzer"],
            "general": ["librarian"]
        }
        return mapping.get(intent, ["librarian"])
    
    def _safety_check(self, state: ConsciousState) -> bool:
        """Deterministic safety validation."""
        dangerous_patterns = [
            r"os\.system", r"subprocess", r"eval\(", r"exec\(",
            r"rm\s+-rf", r"deltree", r"format\s+c:"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, state.query, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                return False
        
        return True


class EffectorRegistry:
    """
    Tool Execution Layer
    Registers all existing modules as 'skills' and executes them safely.
    NOTE: Tools are loaded lazily to avoid circular imports.
    """
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self._tools_registered = False
    
    def _register_builtin_tools(self):
        """Register all existing core modules as tools."""
        if self._tools_registered:
            return
        
        try:
            # Core modules use relative imports, so we need to import them as a package
            import sys
            workspace = Path("/workspace")
            if workspace.exists() and str(workspace) not in sys.path:
                sys.path.insert(0, str(workspace))
            
            # Import core as a package
            import importlib
            core_pkg = importlib.import_module("core")
            
            # Get classes from the package modules
            CodeFixer = getattr(importlib.import_module("core.code_fixer", "core"), "CodeFixer")
            StaticAnalyzer = getattr(importlib.import_module("core.static_analyzer", "core"), "StaticAnalyzer")
            DependencyGraph = getattr(importlib.import_module("core.dependency_graph", "core"), "DependencyGraph")
            SceneGraphAnalyzer = getattr(importlib.import_module("core.scene_graph_analyzer", "core"), "SceneGraphAnalyzer")
            GodotValidator = getattr(importlib.import_module("core.godot_validator", "core"), "GodotValidator")
            CascadeScanner = getattr(importlib.import_module("core.cascade_scanner", "core"), "CascadeScanner")
            Librarian = getattr(importlib.import_module("core.librarian", "core"), "Librarian")
            
            # Instantiate tools (handle dependencies between tools)
            self.tools["code_fixer"] = CodeFixer()
            self.tools["static_analyzer"] = StaticAnalyzer()
            self.tools["dependency_graph"] = DependencyGraph()
            self.tools["scene_graph_analyzer"] = SceneGraphAnalyzer()
            self.tools["godot_validator"] = GodotValidator()
            
            # CascadeScanner requires dependencies - pass them
            try:
                self.tools["cascade_scanner"] = CascadeScanner(
                    dependency_graph=self.tools["dependency_graph"],
                    static_analyzer=self.tools["static_analyzer"]
                )
            except Exception as e:
                logger.warning(f"CascadeScanner needs dependencies: {e}, trying without")
                self.tools["cascade_scanner"] = CascadeScanner.__new__(CascadeScanner)
            
            self.tools["librarian"] = Librarian()
            
            self._tools_registered = True
            logger.info(f"Registered {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Failed to register tools: {e}")
            self._tools_registered = True  # Mark as attempted
    
    def execute(self, tool_name: str, method: str, *args, **kwargs) -> Any:
        """Execute a specific tool method."""
        if not self._tools_registered:
            self._register_builtin_tools()
        
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        if not hasattr(tool, method):
            # Fallback to common methods
            if hasattr(tool, 'analyze'):
                method = 'analyze'
            elif hasattr(tool, 'run'):
                method = 'run'
            elif hasattr(tool, 'search'):
                method = 'search'
            else:
                raise AttributeError(f"Tool {tool_name} has no suitable method")
        
        func = getattr(tool, method)
        return func(*args, **kwargs)
    
    def get_tool_info(self) -> Dict[str, Dict]:
        """Get metadata about registered tools."""
        if not self._tools_registered:
            self._register_builtin_tools()
        
        info = {}
        for name, tool in self.tools.items():
            info[name] = {
                "class": tool.__class__.__name__,
            }
        return info


class EtherConsciousness:
    """
    The Unified Agent Engine
    Replaces ether_engine.py and coordinates all subsystems.
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path or Path.cwd()
        self.hippocampus = Hippocampus(storage_path=self.project_path / ".ether_memory")
        self.cortex = Cortex()
        self.effectors = EffectorRegistry()
        self.current_state: Optional[ConsciousState] = None
        
        # Train cortex on startup
        self._train_default_knowledge()
        
        logger.info(f"Ether Consciousness initialized for project: {self.project_path}")
    
    def _train_default_knowledge(self):
        """Pre-train the cortex with default patterns."""
        training_data = [
            ("fix this bug in my script", "fix_code"),
            ("analyze the dependency graph", "analyze"),
            ("explain how this function works", "explain"),
            ("optimize this loop", "optimize"),
            ("create a new player controller", "generate"),
            ("debug why the scene isn't loading", "debug"),
            ("what is GDScript?", "general"),
            ("help me with my code", "fix_code"),
            ("scan for errors", "analyze"),
            ("check for cascading failures", "debug")
        ]
        self.cortex.train(training_data)
    
    def process(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point: Process a user query through the full consciousness loop.
        1. Perceive (Parse query)
        2. Think (Reason & Plan)
        3. Act (Execute tools)
        4. Learn (Store results)
        """
        logger.info(f"Processing query: {query}")
        
        # 1. Initialize State
        state = ConsciousState(query=query, context=context or {})
        
        # 2. Think (Cortex)
        state = self.cortex.reason(state)
        
        if not state.is_safe:
            return {
                "success": False,
                "error": "Query blocked by safety guard",
                "thought_process": [vars(t) for t in state.thought_chain]
            }
        
        # 3. Act (Effectors)
        results = {}
        for tool_name in state.selected_tools:
            try:
                # Smart method selection based on intent
                method = self._select_method(tool_name, state.intent)
                result = self.effectors.execute(tool_name, method, query, str(self.project_path))
                results[tool_name] = {"status": "success", "data": str(result)[:500]}
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                results[tool_name] = {"status": "error", "message": str(e)}
        
        state.execution_results = results
        
        # 4. Learn (Hippocampus)
        self.hippocampus.store(
            key=f"query_{datetime.now().timestamp()}",
            value={"query": query, "results": results, "intent": state.intent},
            memory_type="short"
        )
        
        # 5. Formulate Response
        response = self._synthesize_response(state)
        
        return {
            "success": True,
            "response": response,
            "intent": state.intent,
            "confidence": state.confidence_score,
            "tools_used": state.selected_tools,
            "results": results,
            "thought_process": [vars(t) for t in state.thought_chain]
        }
    
    def _select_method(self, tool_name: str, intent: str) -> str:
        """Map intent to specific tool methods."""
        defaults = {
            "code_fixer": "analyze",
            "static_analyzer": "analyze",
            "dependency_graph": "analyze",
            "scene_graph_analyzer": "analyze",
            "godot_validator": "validate",
            "cascade_scanner": "scan",
            "librarian": "search"
        }
        return defaults.get(tool_name, "search")
    
    def _synthesize_response(self, state: ConsciousState) -> str:
        """Combine tool results into a coherent natural language response."""
        parts = []
        
        # Intent summary
        parts.append(f"I analyzed your request to '{state.intent}'.")
        
        # Tool results
        for tool, result in state.execution_results.items():
            if result.get("status") == "error":
                continue
            data = result.get("data", "")
            if data:
                parts.append(f"**{tool}**: {data}...")
            else:
                parts.append(f"**{tool}**: Operation completed.")
        
        # Confidence note
        if state.confidence_score < 0.5:
            parts.append("Note: I'm not entirely sure about this analysis. Please verify.")
        
        return "\n\n".join(parts)
    
    def chat(self, query: str) -> str:
        """Simplified chat interface returning just the text response."""
        result = self.process(query)
        return result.get("response", "I encountered an error processing your request.")


# Convenience function for direct usage
def create_consciousness(project_path: Optional[Path] = None) -> EtherConsciousness:
    """Factory function to create a configured consciousness instance."""
    return EtherConsciousness(project_path)


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    agent = create_consciousness()
    
    test_queries = [
        "Fix the bugs in my player script",
        "Analyze the project dependencies",
        "Debug why my scene isn't loading"
    ]
    
    for q in test_queries:
        print(f"\n--- Query: {q} ---")
        response = agent.chat(q)
        print(response)
