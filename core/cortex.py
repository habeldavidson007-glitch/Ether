"""
Ether Cortex - Unified Brain Engine (Phase 11.4: Brain Consolidation)
======================================================================

Merges Builder.py orchestration logic with Consciousness.py neural architecture.

This is THE single entry point for all AI logic in Ether v1.9.8+.

Features:
- Prefetch-first architecture (instant general knowledge)
- Dynamic temperature control (precision vs creativity)
- Auto follow-up generation (autonomous conversation)
- Off-domain guard with prefetch bypass
- Unified search integration
- RAM-aware model selection
"""

import json
import re
import time
import hashlib
import logging
import requests
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Import from unified consciousness module
from ether.core.consciousness import (
    Hippocampus, 
    Cortex as IntentClassifier, 
    SafetyGuard,
    detect_ram_and_suggest_model,
    ML_AVAILABLE
)

# Import supporting modules
from core.unified_search import get_unified_search
from core.adaptive_memory import get_adaptive_memory
from core.safety_preview import get_safety_preview
from core.feedback_commands import get_feedback_manager

logger = logging.getLogger(__name__)


# ── DYNAMIC TEMPERATURE ENGINE (Phase 11.1) ─────────────────────────────────────
# Adjusts creativity vs precision based on intent and conversation context

def get_dynamic_temperature(intent: str, query: str, conversation_history: List[Dict] = None) -> Tuple[float, bool]:
    """
    Dynamically adjust temperature based on intent and context.
    
    Returns: (temperature, use_n_sampling)
    
    Logic:
    - Debug/Fix: Low temp (0.2) for precision
    - Creative/Build: High temp (0.7-0.8) for diversity
    - Explain: Medium temp (0.4-0.5) for clarity
    - Chat: Variable based on conversation flow
    
    N-Sampling: For creative tasks, generate 2-3 variants and pick best
    """
    query_lower = query.lower()
    
    # Precision-critical tasks
    if intent in ['debug', 'fix'] or any(word in query_lower for word in ['error', 'bug', 'broken', 'crash', 'fix']):
        return 0.2, False  # Deterministic, no variation
    
    # Creative tasks benefit from diversity
    if intent in ['build', 'create'] or any(word in query_lower for word in ['create', 'make', 'design', 'implement', 'new feature']):
        return 0.75, True  # High creativity with N-sampling
    
    # Explanations need clarity but some variety
    if intent == 'explain' or any(word in query_lower for word in ['explain', 'what is', 'how does', 'why']):
        return 0.45, False  # Balanced clarity
    
    # Analysis needs moderate creativity
    if intent == 'analyze' or any(word in query_lower for word in ['analyze', 'review', 'optimize', 'improve']):
        return 0.5, False  # Moderate balance
    
    # Chat/conversation - adapt based on history
    if intent == 'chat':
        if conversation_history and len(conversation_history) > 3:
            # Long conversation - add variety to prevent repetition
            return 0.65, True
        else:
            # Short conversation - stay focused
            return 0.5, False
    
    # Default: balanced
    return 0.5, False


def generate_follow_up_questions(query: str, response_text: str, intent: str) -> List[str]:
    """
    Generate 2-3 natural follow-up questions to make conversation feel autonomous.
    
    Uses template-based generation with variability to avoid repetition.
    """
    follow_ups = []
    query_lower = query.lower()
    
    # Intent-specific follow-ups
    if intent in ['debug', 'fix']:
        templates = [
            "Would you like me to explain why this fix works?",
            "Should I check other files for similar issues?",
            "Do you want me to add error handling for this case?",
            "Would you like to see alternative approaches?",
        ]
    elif intent == 'explain':
        templates = [
            "Would you like a code example showing this in action?",
            "Should I explain how this compares to similar concepts?",
            "Do you want to know common pitfalls with this?",
            "Would you like to see advanced usage patterns?",
        ]
    elif intent in ['build', 'create']:
        templates = [
            "Should I add comments to explain the implementation?",
            "Would you like me to create unit tests for this?",
            "Do you want to see how to integrate this with other systems?",
            "Should I optimize this for performance?",
        ]
    elif intent == 'analyze':
        templates = [
            "Would you like me to suggest specific improvements?",
            "Should I create a prioritized action plan?",
            "Do you want me to check for security vulnerabilities?",
            "Would you like a detailed report on code quality?",
        ]
    else:  # chat/general
        templates = [
            "What specific aspect would you like to explore?",
            "Should I provide more details on any part?",
            "Is there a related topic you'd like to discuss?",
            "Would you like practical examples?",
        ]
    
    # Randomly select 2-3 follow-ups
    num_followups = random.randint(2, 3)
    selected = random.sample(templates, min(num_followups, len(templates)))
    
    # Add variability by occasionally rephrasing
    if random.random() > 0.7 and selected:
        # Rephrase one randomly
        idx = random.randint(0, len(selected) - 1)
        variations = {
            "Would you like": "Do you want me to",
            "Should I": "Want me to",
            "Do you want": "Would you prefer",
        }
        for old, new in variations.items():
            if selected[idx].startswith(old):
                selected[idx] = selected[idx].replace(old, new, 1)
                break
    
    return selected


# ── THINKING ENGINE (Deterministic Cognitive Layer) ─────────────────────────
# Converts vague user requests into atomic, bounded instructions for LLM

def _extract_filename(query: str) -> str:
    """Extract .gd filename from query."""
    match = re.search(r'([\w\-]+\.gd)', query.lower())
    return match.group(1) if match else ""


def _decompose_task(query: str) -> dict:
    """
    Decompose user query into action and target.
    Returns: {"action": str, "target": str}
    """
    q = query.lower()

    action = "unknown"
    if "optimize" in q or "improve" in q or "refactor" in q:
        action = "optimize"
    elif "fix" in q or "error" in q or "bug" in q or "broken" in q:
        action = "debug"
    elif "explain" in q or "what" in q or "how" in q:
        action = "explain"
    elif "create" in q or "make" in q or "add" in q:
        action = "build"
    elif "analyze" in q or "check" in q or "review" in q:
        action = "analyze"
    else:
        action = "chat"

    return {
        "action": action,
        "target": _extract_filename(q)
    }


def _cot_fallback(task: dict, analysis: dict, knowledge_context: str = "") -> dict:
    """
    Chain-of-Thought fallback for novel/unrecognized patterns.
    
    Forces the model to:
    1. Analyze the error message/code snippet
    2. Hypothesize 3 potential causes
    3. Select the most likely cause based on Godot best practices
    4. Propose a fix
    
    Returns: {"focus": str, "instruction": str, "limit": str, "cot_prompt": str}
    """
    issues = analysis.get("issues", []) if analysis else []
    issue_str = ", ".join(issues) if issues else "unknown issue"
    task_action = task.get("action", "debug")
    task_file = task.get("file", "unknown file")
    
    # Build CoT prompt that will be injected into the LLM call
    cot_prompt = f"""You are debugging a Godot/GDScript issue. Follow this Chain-of-Thought process:

STEP 1 - ANALYSIS:
- Error/Issue: {issue_str}
- File: {task_file}
- Action Requested: {task_action}
{f"- Knowledge Context: {knowledge_context[:500]}" if knowledge_context else ""}

STEP 2 - HYPOTHESIZE (list 3 potential causes):
1. [First potential cause based on error pattern]
2. [Second potential cause based on code structure]
3. [Third potential cause based on Godot conventions]

STEP 3 - EVALUATE (select most likely):
- Compare each hypothesis against Godot best practices
- Consider common pitfalls in similar scenarios
- Select the hypothesis with strongest evidence

STEP 4 - PROPOSE FIX:
- Provide a minimal, targeted fix addressing the root cause
- Explain why this fix works
- Note any side effects or considerations

Respond with your complete chain-of-thought followed by the concrete fix."""

    return {
        "focus": f"{task_action} via systematic analysis",
        "instruction": f"Apply Chain-of-Thought reasoning to solve: {issue_str}",
        "limit": "max 40 lines including CoT steps",
        "cot_prompt": cot_prompt
    }


# Module-level imports for builder functions (lazy-loaded to avoid circular deps)
def _get_builder_functions():
    """Lazy load builder functions to avoid circular imports and speed up startup"""
    from .builder import analyze, debug, run_pipeline, chat
    return analyze, debug, run_pipeline, chat

class Cortex:
    """
    Unified Cortex Engine - The Consolidated Brain of Ether
    
    Merges:
    - Builder.py orchestration logic (process_query, pipelines)
    - Consciousness.py neural architecture (Hippocampus, Intent Classification)
    - Dynamic temperature control
    - Auto follow-up generation
    - Prefetch-first architecture
    
    This is THE single entry point for all AI queries.
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.hippocampus = Hippocampus()
        self.cortex = IntentClassifier()  # Intent classification
        self.safety = SafetyGuard()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Lazy-loaded components
        self._search_engine = None
        self._memory = None
        self._project_loader = None
        
        # Cache for responses
        self._response_cache = {}
        
        # Detect RAM and suggest model at startup
        suggested_model, available_ram = detect_ram_and_suggest_model()
        self.suggested_model = suggested_model
        self.available_ram_gb = available_ram
        
        logger.info(f"Cortex initialized (Session: {self.session_id}, Model: {suggested_model})")
    
    @property
    def search_engine(self):
        """Lazy load unified search"""
        if self._search_engine is None:
            self._search_engine = get_unified_search(str(self.project_root))
        return self._search_engine
    
    @property
    def memory(self):
        """Lazy load adaptive memory"""
        if self._memory is None:
            self._memory = get_adaptive_memory()
        return self._memory
    
    def is_godot_related(self, query: str) -> bool:
        """
        Check if a query is related to Godot/GDScript development.
        
        Uses a two-tier approach:
        1. Fast keyword heuristic check
        2. Low-threshold ML confidence check for ambiguous cases
        
        Note: This check is bypassed if content is available in prefetch queue
        (allowing general knowledge queries that were pre-fetched).
        
        Returns:
            True if query is Godot-related, False otherwise
        """
        query_lower = query.lower()
        
        # Tier 1: Keyword heuristic check (fast path)
        GODOT_KEYWORDS = {
            "godot", "gdscript", "scene", "node", "shader", "tscn", "gdextension",
            "engine", "viewport", "canvas", "sprite", "kinematic", "rigidbody",
            "area", "collision", "signal", "tween", "animation", "material",
            "texture", "mesh", "light", "camera", "ui", "control", "panel",
            "button", "label", "lineedit", "vbox", "hbox", "grid", "margin",
            "color", "vector2", "vector3", "transform", "basis", "quat", "pool",
            "array", "dictionary", "yield", "await", "coroutine", "rpc", "network",
            "export", "onready", "class_name", "extends", "func", "var", "const",
            "enum", "tool", "editor", "inspector", "filesystem", "debugger"
        }
        
        godot_keyword_count = sum(1 for kw in GODOT_KEYWORDS if kw in query_lower)
        
        # Strong match: 2+ keywords or 1 strong keyword
        strong_keywords = {"godot", "gdscript", "scene", "node", "shader", "tscn", "gdextension"}
        has_strong_keyword = any(kw in query_lower for kw in strong_keywords)
        
        if godot_keyword_count >= 2 or has_strong_keyword:
            return True
        
        # No keywords found - likely off-domain
        if godot_keyword_count == 0:
            return False
        
        # Tier 2: Ambiguous case - use ML classifier with low threshold
        if ML_AVAILABLE and self.cortex.classifier:
            try:
                _, confidence = self.cortex.classify_intent(query)
                return confidence >= 0.3
            except Exception:
                pass
        
        # Default: allow ambiguous queries
        return True
    
    def process_query(self, query: str, yield_steps=None) -> Tuple[Dict, List[str]]:
        """
        Process a user query with intent-aware routing.
        
        Fast Path: Greetings, status, quick help → instant response (<2s)
        Slow Path: Analysis, coding, debugging → full LLM pipeline
        
        PREFETCH-FIRST ARCHITECTURE:
        1. Check prefetch queue for instant general knowledge
        2. Off-domain guard allows prefetched topics
        3. Inject prefetched context into LLM generation
        
        Returns: (result_dict, log_list)
        """
        log = []
        
        def step(name: str):
            log.append(name)
            if yield_steps:
                yield_steps(name)
        
        # STEP 0: PREFETCH QUEUE CHECK - Instant general knowledge
        prefetch_context = None
        used_prefetch = False
        prefetch_result = self.hippocampus.check_prefetch(query)
        if prefetch_result:
            step("⚡ Prefetch hit! Instant knowledge retrieved")
            prefetch_context = prefetch_result.get('content', '')
            used_prefetch = True
        
        # STEP 1: OFF-DOMAIN GUARD - Filter non-Godot queries (BYPASS if prefetch hit)
        if not self.is_godot_related(query) and not used_prefetch:
            step("🚫 Off-domain query detected")
            # Extract topic from query for polite refusal
            stop_words = {"how", "what", "why", "when", "where", "who", "can", "do", "does", "is", "are", "the", "a", "an", "to", "in", "for", "on", "with", "make", "create", "get", "use", "using"}
            words = query.lower().split()
            topic_words = [w for w in words if w not in stop_words and len(w) > 3]
            topic = topic_words[0] if topic_words else "that topic"
            
            refusal = f"Ether is specialized for Godot/GDScript development. I cannot assist with {topic}."
            return {"type": "chat", "text": refusal, "fast_path": True}, log
        
        # STEP 2: Detect intent using fast regex patterns
        fast_intent = self._detect_intent_fast(query)
        
        # STEP 3: Route based on intent
        if fast_intent == 'greeting':
            # FAST PATH: Instant greeting response
            step("⚡ Fast path (greeting)")
            response = self._get_fast_response(fast_intent, query)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'status':
            # FAST PATH: Status from cached stats (no LLM needed)
            step("⚡ Fast path (status)")
            response = self._get_fast_response(fast_intent, query)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'quick_help':
            # FAST PATH: Pre-defined help response
            step("⚡ Fast path (help)")
            response = self._get_fast_response(fast_intent, query)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'explain':
            # FAST PATH: Quick definition/explanation without LLM
            step("⚡ Fast path (explain)")
            response = self._get_fast_response(fast_intent, query)
            # Add follow-up questions to make it conversational
            follow_ups = generate_follow_up_questions(query, response, fast_intent)
            return {"type": "chat", "text": response, "fast_path": True, "follow_ups": follow_ups}, log
        
        else:
            # SLOW PATH: Complex intent requires LLM
            complex_intent = self._classify_complex_intent(query)
            
            # Get dynamic temperature based on intent
            temperature, use_n_sampling = get_dynamic_temperature(complex_intent, query, self.conversation_history)
            step(f"🎨 Temperature: {temperature:.2f}" + (" (N-sampling)" if use_n_sampling else ""))
            
            # Build context (project files + knowledge base + prefetch)
            context = self._build_context(query, complex_intent, prefetch_context)
            
            # Run appropriate pipeline
            if complex_intent == 'analyze':
                result = self._run_analyze_pipeline(query, context, step)
            elif complex_intent in ['debug', 'fix']:
                result = self._run_debug_pipeline(query, context, temperature, use_n_sampling, step)
            elif complex_intent == 'build':
                result = self._run_build_pipeline(query, context, temperature, use_n_sampling, step)
            else:
                result = self._run_chat_pipeline(query, context, temperature, use_n_sampling, step)
            
            # Add follow-ups for conversational flow
            if 'text' in result:
                follow_ups = generate_follow_up_questions(query, result['text'], complex_intent)
                result['follow_ups'] = follow_ups
            
            # Store in conversation history
            self.conversation_history.append({
                "query": query,
                "response": result.get('text', ''),
                "intent": complex_intent,
                "timestamp": datetime.now().isoformat()
            })
            
            return result, log
    
    def _detect_intent_fast(self, query: str) -> str:
        """Fast regex-based intent detection"""
        q = query.lower()
        
        # Greetings
        if re.match(r'^(hi|hello|hey|good morning|good afternoon|good evening)', q):
            return 'greeting'
        
        # Status checks
        if any(word in q for word in ['status', 'health', 'stats', 'overview', 'summary']):
            return 'status'
        
        # Quick help
        if re.match(r'^(help|what can you do|how do i use|commands)', q):
            return 'quick_help'
        
        # Explanations
        if any(phrase in q for phrase in ['what is ', 'what are ', 'explain ', 'how does ', 'define ']):
            return 'explain'
        
        # Default to chat for now
        return 'chat'
    
    def _classify_complex_intent(self, query: str) -> str:
        """Classify complex intents requiring LLM"""
        q = query.lower()
        
        if any(word in q for word in ['analyze', 'review', 'optimize', 'improve', 'refactor']):
            return 'analyze'
        elif any(word in q for word in ['fix', 'error', 'bug', 'broken', 'crash', 'debug']):
            return 'debug'
        elif any(word in q for word in ['create', 'make', 'build', 'implement', 'write', 'generate']):
            return 'build'
        else:
            return 'chat'
    
    def _get_fast_response(self, intent: str, query: str) -> str:
        """Get predefined fast responses"""
        if intent == 'greeting':
            return "Hello! I'm Ether, your Godot AI assistant. How can I help you today?"
        elif intent == 'status':
            return "System operational. Ready to assist with Godot/GDScript development."
        elif intent == 'quick_help':
            return "I can help with: debugging code, explaining concepts, creating features, analyzing projects, and optimizing GDScript. Just ask!"
        elif intent == 'explain':
            # Simple pattern matching for common Godot terms
            explanations = {
                'signal': "Signals in Godot are a way for objects to communicate with each other without being tightly coupled. When an event occurs, an object can emit a signal, and other objects connected to that signal will receive a notification and can respond accordingly.",
                'scene': "A Scene in Godot is a collection of nodes organized in a tree structure. Scenes can be instanced and reused, making them fundamental building blocks of Godot projects.",
                'node': "Nodes are the basic building blocks of Godot. Everything in Godot is a node - from sprites and cameras to UI elements and audio players. Nodes are organized in a tree structure.",
            }
            for term, explanation in explanations.items():
                if term in query.lower():
                    return explanation
            return "That's an interesting question about Godot! Could you provide more context so I can give you a more specific explanation?"
        
        return "I'm ready to help!"
    
    def _build_context(self, query: str, intent: str, prefetch_context: str = None) -> str:
        """Build context from project files, KB, and prefetch"""
        context_parts = []
        
        # Add prefetch context first (if available)
        if prefetch_context:
            context_parts.append(f"[LIVE KNOWLEDGE]\n{prefetch_context}")
        
        # Add unified search results
        if self.search_engine:
            search_results = self.search_engine.search(query, mode="hybrid", top_k=3)
            if search_results:
                for result in search_results:
                    if 'content' in result:
                        source = result.get('source', 'Unknown')
                        context_parts.append(f"# From {source}:\n{result['content'][:500]}")
        
        # Add adaptive memory context
        if self.memory:
            learning_context = self.memory.get_learning_context(query, "")
            if learning_context:
                context_parts.append(f"[PAST LEARNING]\n{learning_context}")
        
        return "\n\n".join(context_parts)
    
    def _run_analyze_pipeline(self, query: str, context: str, step) -> Dict:
        """Run analysis pipeline - wired to builder.py with optimized lazy loading"""
        step("🔍 Analyzing...")
        # Lazy load builder functions
        analyze_func, _, _, _ = _get_builder_functions()
        try:
            result_text = analyze_func(query, context, self.conversation_history)
            return {"type": "analysis", "text": result_text}
        except Exception as e:
            logger.error(f"Analysis pipeline failed: {e}")
            return {"type": "analysis", "text": f"Analysis of: {query}\n\nContext loaded: {len(context)} chars"}
    
    def _run_debug_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """Run debug/fix pipeline - wired to builder.py with optimized lazy loading"""
        step("🐛 Debugging...")
        # Lazy load builder functions
        _, debug_func, _, _ = _get_builder_functions()
        try:
            result = debug_func(query, context)
            return {"type": "debug", "text": result.get("explanation", str(result)), "changes": result.get("changes", [])}
        except Exception as e:
            logger.error(f"Debug pipeline failed: {e}")
            return {"type": "debug", "text": f"Debugging: {query}\n\nTemperature: {temperature}"}
    
    def _run_build_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """Run build/create pipeline - wired to builder.py with optimized lazy loading"""
        step("🔨 Building...")
        # Lazy load builder functions
        _, _, run_pipeline_func, _ = _get_builder_functions()
        try:
            result, _ = run_pipeline_func(
                task=query,
                intent="build",
                context=context,
                history=self.conversation_history,
                yield_steps=step
            )
            return result
        except Exception as e:
            logger.error(f"Build pipeline failed: {e}")
            return {"type": "build", "text": f"Creating: {query}\n\nTemperature: {temperature}"}
    
    def _run_chat_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """Run general chat pipeline - wired to builder.py with optimized lazy loading"""
        step("💬 Chatting...")
        # Lazy load builder functions
        _, _, _, chat_func = _get_builder_functions()
        try:
            result_text = chat_func(query, self.conversation_history, context)
            return {"type": "chat", "text": result_text}
        except Exception as e:
            logger.error(f"Chat pipeline failed: {e}")
            return {"type": "chat", "text": f"Response to: {query}\n\nTemperature: {temperature}"}


# Singleton instance
_cortex_instance: Optional[Cortex] = None

def get_cortex(project_root: str = None) -> Cortex:
    """Get or create Cortex singleton instance"""
    global _cortex_instance
    if _cortex_instance is None:
        _cortex_instance = Cortex(project_root)
    return _cortex_instance


# ── ALIAS FOR BACKWARD COMPATIBILITY ─────────────────────────────────────
# Export run_pipeline and EtherBrain from builder.py for backward compatibility
# This allows code to import from cortex.py while implementations still live in builder.py

from .builder import run_pipeline, EtherBrain

__all__ = ["run_pipeline", "EtherBrain"]
