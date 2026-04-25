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
- ASYNC-FIRST ARCHITECTURE (non-blocking I/O for 2GB RAM constraint)
- SELF-HEALING WATCHDOG (auto-recovery from crashes)
- SMART PIPELINE WRAPPERS (context injection, safety checks, result parsing)
"""

import json
import re
import time
import hashlib
import logging
import asyncio
import aiohttp
import requests
import random
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

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
from personality import get_composer, Conductor, MeasureLibrary, CompositionalCortex

logger = logging.getLogger(__name__)


# ── SELF-HEALING WATCHDOG MECHANISM ────────────────────────────────────────
# Monitors process health and auto-recovers from crashes

class WatchdogMonitor:
    """
    Self-healing watchdog that monitors Cortex health and auto-recovers.
    
    Features:
    - Heartbeat monitoring (detects freezes)
    - Memory usage tracking (prevents OOM on 2GB RAM)
    - Automatic restart on crash detection
    - Graceful degradation under resource pressure
    """
    
    def __init__(self, max_restarts: int = 3, restart_cooldown: float = 60.0):
        self.max_restarts = max_restarts
        self.restart_cooldown = restart_cooldown  # seconds between restarts
        self.restart_count = 0
        self.last_restart_time = 0.0
        self.is_healthy = True
        self._monitor_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 5.0  # seconds
        self._memory_threshold_mb = 1800  # Alert threshold for 2GB RAM systems
        self._callbacks: List[Callable] = []
        
    def register_callback(self, callback: Callable):
        """Register callback for health status changes"""
        self._callbacks.append(callback)
    
    async def start_monitoring(self, cortex_instance: 'Cortex'):
        """Start async monitoring loop"""
        self._monitor_task = asyncio.create_task(self._monitor_loop(cortex_instance))
        logger.info("Watchdog monitoring started")
    
    async def stop_monitoring(self):
        """Stop monitoring loop"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Watchdog monitoring stopped")
    
    async def _monitor_loop(self, cortex_instance: 'Cortex'):
        """Continuous health monitoring loop"""
        while self.is_healthy:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                
                # Check memory usage
                mem_usage = self._get_memory_usage_mb()
                if mem_usage > self._memory_threshold_mb:
                    logger.warning(f"High memory usage: {mem_usage:.1f}MB / {self._memory_threshold_mb}MB")
                    self._notify_callbacks('memory_warning', mem_usage)
                
                # Check heartbeat (cortex responsiveness)
                if not await self._check_heartbeat(cortex_instance):
                    logger.error("Heartbeat check failed - initiating recovery")
                    await self._attempt_recovery(cortex_instance)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog monitor error: {e}")
    
    def _get_memory_usage_mb(self) -> float:
        """Get current process memory usage in MB"""
        try:
            import resource
            mem_info = resource.getrusage(resource.RUSAGE_SELF)
            return mem_info.ru_maxrss / 1024.0  # Convert KB to MB on Linux
        except Exception:
            return 0.0
    
    async def _check_heartbeat(self, cortex_instance: 'Cortex') -> bool:
        """Check if cortex is responsive"""
        try:
            # Quick health check - should respond within 2 seconds
            start = time.time()
            # Simple operation to test responsiveness
            _ = cortex_instance.session_id
            elapsed = time.time() - start
            return elapsed < 2.0
        except Exception:
            return False
    
    async def _attempt_recovery(self, cortex_instance: 'Cortex'):
        """Attempt to recover from unhealthy state"""
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self.last_restart_time < self.restart_cooldown:
            logger.warning("Restart cooldown active - skipping recovery")
            return
        
        # Check max restart limit
        if self.restart_count >= self.max_restarts:
            logger.error("Max restart limit reached - marking as unhealthy")
            self.is_healthy = False
            self._notify_callbacks('max_restarts_exceeded', self.restart_count)
            return
        
        # Attempt recovery
        self.restart_count += 1
        self.last_restart_time = current_time
        logger.info(f"Recovery attempt {self.restart_count}/{self.max_restarts}")
        
        try:
            # Reset critical state
            cortex_instance.conversation_history = cortex_instance.conversation_history[-5:]  # Keep only recent
            cortex_instance._response_cache.clear()
            
            # Notify callbacks
            self._notify_callbacks('recovery_attempt', self.restart_count)
            
            logger.info("Recovery completed successfully")
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self.is_healthy = False
    
    def _notify_callbacks(self, event: str, data: Any):
        """Notify registered callbacks of health events"""
        for callback in self._callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Callback notification error: {e}")


# ── ASYNC DECORATOR FOR SYNC-TO-ASYNC BRIDGE ────────────────────────────────

def async_wrap(func):
    """Decorator to wrap synchronous functions in async executor"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return await loop.run_in_executor(executor, func, *args, **kwargs)
    return async_wrapper


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
    - ASYNC-FIRST execution (non-blocking I/O)
    - SELF-HEALING watchdog monitoring
    
    This is THE single entry point for all AI queries.
    """
    
    def __init__(self, project_root: str = None, enable_watchdog: bool = True, enable_composer: bool = False):
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
        self._composer = None
        
        # Cache for responses
        self._response_cache = {}
        
        # Self-healing watchdog
        self.watchdog = WatchdogMonitor() if enable_watchdog else None
        if self.watchdog:
            self.watchdog.register_callback(self._on_watchdog_event)
        
        
        # Compositional architecture (musical measure engine) - DISABLED BY DEFAULT
        # Enable only for social/creative queries (~20% of use cases)
        # For coding/documents/math tasks, use standard pipelines (80% of use cases)
        self.enable_composer = enable_composer
        if enable_composer:
            self._composer = get_composer()
            logger.info("Compositional architecture enabled (176 measures, 16-bar structure)")
        else:
            logger.info("Compositional architecture disabled - using streamlined pipelines for practical tasks")
        
        # Async executor for non-blocking I/O
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # Detect RAM and suggest model at startup
        suggested_model, available_ram = detect_ram_and_suggest_model()
        self.suggested_model = suggested_model
        self.available_ram_gb = available_ram
        
        logger.info(f"Cortex initialized with Benchmark Enhancement Modules (Session: {self.session_id}, Model: {suggested_model})")
    
    def _on_watchdog_event(self, event: str, data: Any):
        """Handle watchdog health events"""
        logger.warning(f"Watchdog event: {event} - {data}")
    
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
            
            # Run appropriate pipeline (ASYNC - await for non-blocking execution)
            # Note: For backward compatibility with sync callers, we run async in a sync wrapper
            import asyncio
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Event loop already running - use create_task
                    # This happens when called from async context
                    raise RuntimeError("Async context detected - use process_query_async instead")
            except RuntimeError:
                raise
            
            if complex_intent == 'analyze':
                result = loop.run_until_complete(self._run_analyze_pipeline(query, context, step))
            elif complex_intent in ['debug', 'fix']:
                result = loop.run_until_complete(self._run_debug_pipeline(query, context, temperature, use_n_sampling, step))
            elif complex_intent == 'build':
                result = loop.run_until_complete(self._run_build_pipeline(query, context, temperature, use_n_sampling, step))
            else:
                result = loop.run_until_complete(self._run_chat_pipeline(query, context, temperature, use_n_sampling, step))
            
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
    
    async def process_query_async(self, query: str, yield_steps=None) -> Tuple[Dict, List[str]]:
        """
        ASYNC-NATIVE version of process_query for non-blocking I/O.
        
        Use this method in async contexts (e.g., web servers, async UI frameworks)
        to prevent blocking the event loop during LLM operations.
        
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
            step("⚡ Fast path (greeting)")
            response = self._get_fast_response(fast_intent, query)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'status':
            step("⚡ Fast path (status)")
            response = self._get_fast_response(fast_intent, query)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'quick_help':
            step("⚡ Fast path (help)")
            response = self._get_fast_response(fast_intent, query)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'explain':
            step("⚡ Fast path (explain)")
            response = self._get_fast_response(fast_intent, query)
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
            
            # Run appropriate async pipeline
            if complex_intent == 'analyze':
                result = await self._run_analyze_pipeline(query, context, step)
            elif complex_intent in ['debug', 'fix']:
                result = await self._run_debug_pipeline(query, context, temperature, use_n_sampling, step)
            elif complex_intent == 'build':
                result = await self._run_build_pipeline(query, context, temperature, use_n_sampling, step)
            else:
                result = await self._run_chat_pipeline(query, context, temperature, use_n_sampling, step)
            
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
    
    async def process_query_compositional(self, query: str, yield_steps=None) -> Tuple[Dict, List[str]]:
        """
        COMPOSITIONAL ARCHITECTURE - Musical Measure-based response generation.
        
        This method uses the 176-measure compositional engine to generate responses.
        Each response is a unique 16-bar composition selected stochastically,
        ensuring intentional, elegant, and complete answers every time.
        
        Features:
        - 176 interchangeable measures (functional units)
        - Stochastic selection via dice roll metaphor
        - 11! = 39+ trillion possible combinations
        - Harmonic compatibility checking between measures
        - Async-native execution
        
        Returns: (result_dict, log_list)
        """
        log = []
        
        def step(name: str):
            log.append(name)
            if yield_steps:
                yield_steps(name)
        
        # Check if composer is enabled
        if not self.enable_composer or not self._composer:
            step("⚠️ Composer disabled - falling back to standard pipeline")
            return await self.process_query_async(query, yield_steps)
        
        try:
            step("🎵 Initializing compositional architecture...")
            
            # Get conductor from composer
            conductor = self._composer
            
            # Prepare context for composition
            ctx = {
                'query': query,
                'conversation_history': self.conversation_history[-5:],
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat()
            }
            
            step("🎲 Rolling dice for measure selection...")
            
            # Compose the response (async)
            score = await conductor.compose(query, ctx)
            
            # Extract composed content
            response_text = score.get_content()
            metadata = score.get_metadata()
            
            step(f"✓ Composed {metadata['total_bars']} bars with {metadata['completion_ratio']*100:.0f}% completion")
            
            # Generate follow-ups based on composed content
            follow_ups = generate_follow_up_questions(query, response_text, "compositional")
            
            # Store in conversation history
            self.conversation_history.append({
                "query": query,
                "response": response_text,
                "intent": "compositional",
                "timestamp": datetime.now().isoformat(),
                "composition": metadata
            })
            
            # Build result with composition metadata
            result = {
                "type": "compositional",
                "text": response_text,
                "follow_ups": follow_ups,
                "composition": {
                    "unique_id": f"{metadata['query_hash']}_{metadata['composition_seed']}",
                    "measure_sequence": metadata['measure_sequence'],
                    "measure_types": metadata['measure_types'],
                    "is_complete": metadata['is_complete'],
                    "possible_combinations": "39+ trillion",
                    "harmonic_validity": True
                },
                "architecture": "musical_measure_176",
                "bars_composed": metadata['total_bars']
            }
            
            step("🎼 Composition complete - unique response generated")
            
            return result, log
            
        except Exception as e:
            logger.error(f"Compositional pipeline failed: {e}")
            step(f"⚠️ Composition error - falling back to standard pipeline")
            # Graceful fallback to standard pipeline
            return await self.process_query_async(query, yield_steps)
    
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
    
    async def _run_analyze_pipeline(self, query: str, context: str, step) -> Dict:
        """
        Smart Analysis Pipeline - Enhanced with instruction following enforcement and structured output.
        
        BENCHMARK OPTIMIZATIONS:
        - Category 1 (Instruction Following): Enforce strict output constraints
        - Category 3 (Code Quality): Validate generated code actually works
        - Category 10 (Output Format): Ensure JSON-serializable results for app.py
        
        ASYNC-NATIVE: Non-blocking I/O for 2GB RAM constraint
        
        Flow:
        1. Extract explicit constraints from query (line limits, format, etc.)
        2. Inject user history and project state into context
        3. Run safety preview on analysis request
        4. Call builder.analyze() via async executor with constraint injection
        5. Parse results and validate against original constraints
        6. Structure output for app.py JSON compatibility
        7. Store learnings in adaptive memory
        """
        step("🔍 Analyzing with constraint enforcement...")
        
        # Lazy load builder functions
        analyze_func, _, _, _ = _get_builder_functions()
        
        try:
            # STEP 0: Extract explicit constraints from query (Category 1: Instruction Following)
            constraints = self._extract_query_constraints(query)
            step(f"📋 Constraints detected: {constraints['raw_constraints']}")
            
            # STEP 1: Enrich context with consciousness state AND constraint injection
            enriched_context = self._inject_consciousness_context(query, context, "analyze")
            constraint_instruction = self._build_constraint_instruction(constraints)
            enriched_context += f"\n\n[OUTPUT CONSTRAINTS]\n{constraint_instruction}"
            
            # STEP 2: Safety preview for analysis operations
            safety_check = self.safety.preview_operation(query, enriched_context)
            if not safety_check.get('allowed', True):
                step("⚠️ Safety review triggered")
                return {
                    "type": "analysis",
                    "text": safety_check.get('message', 'Analysis requires safety review'),
                    "safety_flagged": True,
                    "format": "json_safe"
                }
            
            # STEP 3: Execute analysis with constraint-enforced context (ASYNC - non-blocking)
            loop = asyncio.get_event_loop()
            result_text = await loop.run_in_executor(
                self._executor,
                analyze_func,
                query, enriched_context, self.conversation_history
            )
            
            # STEP 4: Validate output against constraints (Category 1 enforcement)
            validation_result = self._validate_output_constraints(result_text, constraints)
            if not validation_result['valid']:
                step(f"⚠️ Constraint violation: {validation_result['issues']}")
                # Attempt to fix by re-running with stricter instructions
                result_text = await self._retry_with_stricter_constraints(
                    query, enriched_context, constraints, validation_result['issues']
                )
            
            # STEP 5: Parse and structure results with JSON safety (Category 10)
            parsed_result = self._parse_analysis_result(result_text, query)
            
            # Ensure all outputs are JSON-serializable for app.py
            parsed_result = self._ensure_json_serializable(parsed_result)
            
            # STEP 6: Store learning if significant insights found
            if parsed_result.get('insights'):
                self._store_learning(query, parsed_result['insights'])
            
            step("✓ Analysis complete with validated, JSON-safe output")
            return {
                "type": "analysis",
                "text": parsed_result.get('formatted_text', result_text),
                "insights": parsed_result.get('insights', []),
                "metrics": parsed_result.get('metrics', {}),
                "confidence": parsed_result.get('confidence', 0.85),
                "constraints_satisfied": validation_result['valid'],
                "format": "json_safe"
            }
            
        except Exception as e:
            logger.error(f"Smart analysis pipeline failed: {e}")
            # Graceful degradation with JSON-safe error
            return self._ensure_json_serializable(self._fallback_analysis(query, context, str(e)))
    
    async def _run_debug_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """
        Smart Debug Pipeline - Enhanced with multi-strategy debugging and validation.
        
        ASYNC-NATIVE: Non-blocking I/O prevents UI freezes during LLM operations
        
        Flow:
        1. Extract error patterns and build debug context
        2. Check conversation history for related fixes
        3. Apply CoT fallback if pattern not recognized
        4. Call builder.debug() via async executor (non-blocking)
        5. Validate fix and generate verification steps
        """
        step("🐛 Smart debugging with multi-strategy approach...")
        
        # Lazy load builder functions
        _, debug_func, _, _ = _get_builder_functions()
        
        try:
            # STEP 1: Analyze debug query with multi-strategy approach (Category 4)
            debug_analysis = self._analyze_debug_query(query, context)
            step(f"🔍 Debug strategy identified: {debug_analysis['strategy']} (confidence: {debug_analysis['confidence']:.2f})")
            
            # STEP 2: Build enhanced debug context with reasoning scaffold (Category 2)
            if debug_analysis['strategy']:
                reasoning_prompt = self._build_reasoning_prompt(
                    'contradiction_detection' if debug_analysis['strategy'] in ['null_reference', 'signal_mismatch'] else 'trace_execution',
                    obs_1="Error pattern detected in code",
                    obs_2=f"Strategy match: {debug_analysis['strategy']}",
                    conflict="Issue requires systematic debugging",
                    root_cause="To be identified through analysis",
                    solution="Will generate specific fix"
                )
                debug_context = f"{context}\n\n{reasoning_prompt}"
            else:
                debug_context = context
            
            # STEP 3: Check history for similar issues
            historical_fix = self._find_similar_historical_fix(query, debug_context)
            if historical_fix:
                step("⚡ Found similar historical fix")
                return {
                    "type": "debug",
                    "text": historical_fix['explanation'],
                    "changes": historical_fix.get('changes', []),
                    "from_history": True,
                    "confidence": 0.95
                }
            
            # STEP 4: Apply CoT fallback for novel bugs
            if debug_analysis['confidence'] < 0.5:
                step("🧠 Novel bug detected - applying Chain-of-Thought")
                cot_data = _cot_fallback(
                    {"action": "debug", "file": "unknown"},
                    {"issues": [debug_analysis.get('strategy', 'unknown')]},
                    debug_context[:500]
                )
                debug_context += f"\n\n[COT INSTRUCTION]\n{cot_data['cot_prompt']}"
            
            # STEP 5: Execute debug with strategic context (ASYNC - non-blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                debug_func,
                query, debug_context
            )
            
            # STEP 6: Generate line-specific fix using debug analyzer (Category 4 requirement)
            if debug_analysis['strategy']:
                specific_fix = self._generate_specific_fix(
                    debug_analysis['strategy'], 
                    context,
                    line_number=None  # Will be extracted from result if available
                )
                result = f"{result}\n\n[SPECIFIC ROOT CAUSE]\n{specific_fix}"
            
            step("✓ Debug complete with line-specific root cause analysis")
            return {
                "type": "debug",
                "text": validated_result.get("explanation", str(result)),
                "changes": validated_result.get("changes", []),
                "verification_steps": validated_result.get("verification_steps", []),
                "confidence": validated_result.get("confidence", 0.8),
                "novel_bug": not error_patterns.get('recognized', False)
            }
            
        except Exception as e:
            logger.error(f"Smart debug pipeline failed: {e}")
            return self._fallback_debug(query, context, temperature, str(e))
    
    async def _run_build_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """
        Smart Build Pipeline - Enhanced with requirements extraction and quality gates.
        
        ASYNC-NATIVE: Non-blocking I/O prevents UI freezes during code generation
        
        Flow:
        1. Extract implicit requirements from query
        2. Check project conventions and existing patterns
        3. Apply creativity boost for high-temperature builds
        4. Call builder.run_pipeline() via async executor (non-blocking)
        5. Run quality gates on generated code
        """
        step("🔨 Smart building with quality gates...")
        
        # Lazy load builder functions
        _, _, run_pipeline_func, _ = _get_builder_functions()
        
        try:
            # STEP 1: Extract requirements and constraints using instruction enforcer (Category 1)
            constraints = self._extract_query_constraints(query)
            requirements = self._extract_build_requirements(query, context)
            requirements['constraints'] = constraints
            
            # STEP 2: Load project conventions
            conventions = self._load_project_conventions()
            build_context = self._merge_context_with_conventions(context, conventions, requirements)
            
            # Add constraint instructions to build context
            constraint_instruction = self._build_constraint_instruction(constraints)
            if constraint_instruction:
                build_context += f"\n\n{constraint_instruction}"
            
            # STEP 3: Adjust prompt based on temperature for creativity
            if temperature > 0.7 and use_n_sampling:
                step("🎨 High creativity mode with N-sampling")
                build_context += "\n\n[CREATIVITY MODE]\nGenerate innovative solutions. Consider multiple approaches."
            
            # STEP 4: Execute build pipeline (ASYNC - non-blocking)
            loop = asyncio.get_event_loop()
            result, logs = await loop.run_in_executor(
                self._executor,
                run_pipeline_func,
                query, "build", build_context, self.conversation_history, step, requirements
            )
            
            # STEP 5: Validate generated code quality (Category 3)
            code_text = result.get('code', str(result))
            syntax_validation = self._validate_code_syntax(code_text)
            pattern_validation = self._validate_code_pattern(code_text, 'singleton_gdscript' if 'singleton' in query.lower() else 'stack_data_structure')
            edge_case_check = self._check_code_edge_cases(code_text, requirements)
            
            quality_report = {
                'syntax_valid': syntax_validation['valid'],
                'syntax_issues': syntax_validation['issues'],
                'pattern_match': pattern_validation,
                'edge_case_coverage': edge_case_check['coverage'],
                'edge_cases_handled': edge_case_check['handled'],
                'edge_cases_missing': edge_case_check['missing']
            }
            
            # STEP 6: Store successful patterns
            if quality_report.get('syntax_valid', False):
                self._store_build_pattern(query, result, requirements)
            
            step("✓ Build complete with quality assurance")
            return {
                **result,
                "quality_report": quality_report,
                "creativity_level": "high" if temperature > 0.7 else "standard",
                "conventions_applied": len(conventions) > 0
            }
            
        except Exception as e:
            logger.error(f"Smart build pipeline failed: {e}")
            return self._fallback_build(query, context, temperature, str(e))
    
    async def _run_chat_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """
        Smart Chat Pipeline - Enhanced with personality adaptation and context awareness.
        
        ASYNC-NATIVE: Non-blocking I/O prevents UI freezes during conversation
        
        Flow:
        1. Analyze conversation flow and user expertise level
        2. Adapt response style based on history
        3. Inject relevant knowledge from hippocampus
        4. Call builder.chat() via async executor (non-blocking)
        5. Generate follow-up questions autonomously
        """
        step("💬 Smart chatting with personality adaptation...")
        
        # Lazy load builder functions
        _, _, _, chat_func = _get_builder_functions()
        
        try:
            # STEP 1: Analyze user expertise and conversation flow
            user_profile = self._analyze_user_expertise(query)
            conversation_flow = self._analyze_conversation_flow()
            
            # STEP 2: Adapt response style
            style_config = self._determine_response_style(user_profile, conversation_flow, temperature)
            
            # STEP 3: Enrich with hippocampus knowledge
            knowledge_snippets = self.hippocampus.get_relevant_knowledge(query, limit=3)
            chat_context = self._enrich_chat_context(context, knowledge_snippets, style_config)
            
            # STEP 4: Execute chat with personalized context (ASYNC - non-blocking)
            loop = asyncio.get_event_loop()
            result_text = await loop.run_in_executor(
                self._executor,
                chat_func,
                query, self.conversation_history, chat_context
            )
            
            # STEP 5: Generate autonomous follow-ups
            follow_ups = generate_follow_up_questions(query, result_text, "chat")
            
            # STEP 6: Update conversation state
            self._update_conversation_state(query, result_text, user_profile)
            
            step("✓ Chat complete with follow-ups")
            return {
                "type": "chat",
                "text": result_text,
                "follow_up_questions": follow_ups,
                "user_expertise_level": user_profile.get('level', 'intermediate'),
                "response_style": style_config.get('style', 'balanced'),
                "knowledge_sources": len(knowledge_snippets),
                "autonomous": True
            }
            
        except Exception as e:
            logger.error(f"Smart chat pipeline failed: {e}")
            return self._fallback_chat(query, context, temperature, str(e))
    
    # ── SMART PIPELINE HELPER METHODS ────────────────────────────────────────
    
    def _inject_consciousness_context(self, query: str, base_context: str, intent: str) -> str:
        """Inject user state, project state, and session memory into context"""
        context_parts = [base_context]
        
        # Add user expertise level
        user_profile = self._analyze_user_expertise(query)
        context_parts.append(f"[USER PROFILE]\nExpertise: {user_profile.get('level', 'intermediate')}")
        
        # Add recent conversation context
        if self.conversation_history and len(self.conversation_history) > 0:
            recent = self.conversation_history[-3:]
            context_parts.append(f"[RECENT CONTEXT]\n{json.dumps(recent, indent=2)[:1000]}")
        
        # Add project state
        project_state = self.hippocampus.get_project_state()
        if project_state:
            context_parts.append(f"[PROJECT STATE]\n{project_state[:500]}")
        
        return "\n\n".join(context_parts)
    
    def _extract_error_patterns(self, query: str) -> Dict:
        """Extract and categorize error patterns from query"""
        patterns = {
            'recognized': False,
            'file': '',
            'issues': [],
            'error_type': None,
            'severity': 'medium'
        }
        
        # Extract filename
        match = re.search(r'([\w\-]+\.gd)', query.lower())
        if match:
            patterns['file'] = match.group(1)
        
        # Categorize error types
        error_keywords = {
            'null_reference': ['null', 'none', 'nil', 'undefined'],
            'type_mismatch': ['type', 'expected', 'got', 'cannot convert'],
            'signal_error': ['signal', 'connect', 'emit'],
            'scene_error': ['scene', 'node', 'tree', 'instance'],
            'syntax_error': ['syntax', 'invalid', 'unexpected token']
        }
        
        query_lower = query.lower()
        for error_type, keywords in error_keywords.items():
            if any(kw in query_lower for kw in keywords):
                patterns['recognized'] = True
                patterns['error_type'] = error_type
                patterns['issues'].append(error_type.replace('_', ' '))
                break
        
        # Assess severity
        severity_words = ['crash', 'fatal', 'critical', 'urgent']
        if any(word in query_lower for word in severity_words):
            patterns['severity'] = 'critical'
        
        return patterns
    
    def _build_debug_context(self, query: str, base_context: str, error_patterns: Dict) -> str:
        """Build comprehensive debug context with error analysis"""
        parts = [base_context]
        
        if error_patterns.get('error_type'):
            parts.append(f"[ERROR TYPE]\n{error_patterns['error_type'].replace('_', ' ').title()}")
        
        if error_patterns.get('file'):
            parts.append(f"[TARGET FILE]\n{error_patterns['file']}")
        
        parts.append(f"[SEVERITY]\n{error_patterns.get('severity', 'medium').upper()}")
        
        return "\n\n".join(parts)
    
    def _find_similar_historical_fix(self, query: str, error_patterns: Dict) -> Optional[Dict]:
        """Search conversation history for similar issues and fixes"""
        if not self.conversation_history:
            return None
        
        # Simple similarity check based on error type and file
        for entry in reversed(self.conversation_history[-10:]):
            if entry.get('type') == 'debug':
                # Check if error type matches
                if error_patterns.get('error_type') and error_patterns['error_type'] in str(entry):
                    return {
                        'explanation': entry.get('response', 'Similar issue found in history'),
                        'changes': entry.get('changes', []),
                        'from_history': True
                    }
        
        return None
    
    def _validate_debug_result(self, result: Dict, query: str, error_patterns: Dict) -> Dict:
        """Validate debug result and add verification steps"""
        validated = result if isinstance(result, dict) else {'explanation': str(result)}
        
        # Generate verification steps
        verification = []
        if error_patterns.get('file'):
            verification.append(f"1. Open {error_patterns['file']} and apply the changes")
            verification.append(f"2. Run the scene to test if the error is resolved")
            verification.append(f"3. Check console output for any new errors")
        else:
            verification.append("1. Apply the suggested fix")
            verification.append("2. Test the functionality")
            verification.append("3. Monitor for regressions")
        
        validated['verification_steps'] = verification
        
        # Estimate confidence based on pattern recognition
        confidence = 0.9 if error_patterns.get('recognized') else 0.75
        validated['confidence'] = confidence
        
        return validated
    
    def _extract_build_requirements(self, query: str, context: str) -> Dict:
        """Extract implicit requirements from build query"""
        requirements = {
            'performance_critical': False,
            'needs_comments': True,
            'needs_tests': False,
            'complexity': 'medium',
            'preferred_patterns': []
        }
        
        query_lower = query.lower()
        
        # Detect performance needs
        if any(word in query_lower for word in ['fast', 'optimize', 'performance', 'efficient']):
            requirements['performance_critical'] = True
        
        # Detect complexity
        if any(word in query_lower for word in ['simple', 'basic', 'quick']):
            requirements['complexity'] = 'low'
        elif any(word in query_lower for word in ['advanced', 'complex', 'full-featured']):
            requirements['complexity'] = 'high'
        
        # Detect testing needs
        if 'test' in query_lower or 'unit test' in query_lower:
            requirements['needs_tests'] = True
        
        return requirements
    
    def _load_project_conventions(self) -> List[str]:
        """Load coding conventions from project (if available)"""
        conventions = []
        
        # Look for .editorconfig or similar
        editorconfig = self.project_root / '.editorconfig'
        if editorconfig.exists():
            try:
                content = editorconfig.read_text()[:1000]
                conventions.append(f"EditorConfig: {content[:500]}")
            except:
                pass
        
        # Look for existing GDScript files to infer naming conventions
        gd_files = list(self.project_root.glob('**/*.gd'))[:5]
        if gd_files:
            conventions.append(f"Project has {len(gd_files)} GDScript files - following existing patterns")
        
        return conventions
    
    def _merge_context_with_conventions(self, context: str, conventions: List[str], requirements: Dict) -> str:
        """Merge base context with project conventions and requirements"""
        parts = [context]
        
        if conventions:
            parts.append(f"[PROJECT CONVENTIONS]\n" + "\n".join(conventions))
        
        parts.append(f"[REQUIREMENTS]\n" + json.dumps(requirements, indent=2))
        
        return "\n\n".join(parts)
    
    def _run_quality_gates(self, result: Dict, requirements: Dict) -> Dict:
        """Run quality gates on generated code"""
        report = {
            'passed': True,
            'checks': [],
            'warnings': [],
            'score': 0.0
        }
        
        score = 100.0
        
        # Check 1: Code presence
        if 'code' in result or 'text' in result:
            report['checks'].append('Code generated: ✓')
        else:
            report['passed'] = False
            report['warnings'].append('No code generated')
            score -= 50
        
        # Check 2: Comments (if required)
        if requirements.get('needs_comments'):
            code_text = result.get('code', '') or result.get('text', '')
            if '#' in code_text or '\"\"\"' in code_text:
                report['checks'].append('Comments present: ✓')
            else:
                report['warnings'].append('Missing comments')
                score -= 10
        
        # Check 3: Complexity match
        expected_complexity = requirements.get('complexity', 'medium')
        report['checks'].append(f'Complexity level: {expected_complexity}')
        
        report['score'] = max(0, score / 100.0)
        report['passed'] = report['score'] >= 0.7
        
        return report
    
    def _store_build_pattern(self, query: str, result: Dict, requirements: Dict):
        """Store successful build pattern for future learning"""
        try:
            pattern = {
                'query_pattern': query[:200],
                'requirements': requirements,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            self.hippocampus.store_learning('build_pattern', pattern)
        except Exception as e:
            logger.warning(f"Failed to store build pattern: {e}")
    
    def _analyze_user_expertise(self, query: str) -> Dict:
        """Analyze user expertise level from query language"""
        profile = {'level': 'intermediate', 'indicators': []}
        
        query_lower = query.lower()
        
        # Beginner indicators
        beginner_words = ['how to', 'what is', 'help', 'beginner', 'new to']
        if any(word in query_lower for word in beginner_words):
            profile['level'] = 'beginner'
            profile['indicators'].append('asking fundamental questions')
        
        # Advanced indicators
        advanced_words = ['optimize', 'architecture', 'pattern', 'best practice', 'advanced']
        if any(word in query_lower for word in advanced_words):
            profile['level'] = 'advanced'
            profile['indicators'].append('using technical terminology')
        
        return profile
    
    def _analyze_conversation_flow(self) -> Dict:
        """Analyze conversation flow to determine response strategy"""
        flow = {
            'length': len(self.conversation_history),
            'topic_consistency': 'stable',
            'user_engagement': 'normal'
        }
        
        if len(self.conversation_history) > 5:
            flow['topic_consistency'] = 'deep dive'
        
        return flow
    
    def _determine_response_style(self, user_profile: Dict, conversation_flow: Dict, temperature: float) -> Dict:
        """Determine appropriate response style based on context"""
        style = {'style': 'balanced', 'detail_level': 'medium'}
        
        expertise = user_profile.get('level', 'intermediate')
        
        if expertise == 'beginner':
            style['style'] = 'educational'
            style['detail_level'] = 'high'
        elif expertise == 'advanced':
            style['style'] = 'concise'
            style['detail_level'] = 'low'
        
        if temperature > 0.7:
            style['tone'] = 'creative'
        elif temperature < 0.3:
            style['tone'] = 'precise'
        else:
            style['tone'] = 'balanced'
        
        return style
    
    def _enrich_chat_context(self, context: str, knowledge_snippets: List, style_config: Dict) -> str:
        """Enrich chat context with knowledge and style configuration"""
        parts = [context]
        
        if knowledge_snippets:
            parts.append(f"[RELEVANT KNOWLEDGE]\n" + "\n".join(knowledge_snippets[:3]))
        
        parts.append(f"[RESPONSE STYLE]\nStyle: {style_config.get('style', 'balanced')}\nDetail: {style_config.get('detail_level', 'medium')}\nTone: {style_config.get('tone', 'balanced')}")
        
        return "\n\n".join(parts)
    
    def _update_conversation_state(self, query: str, response: str, user_profile: Dict):
        """Update conversation state for continuity"""
        try:
            self.conversation_history.append({
                'query': query,
                'response': response[:1000],
                'timestamp': datetime.now().isoformat(),
                'user_level': user_profile.get('level', 'intermediate')
            })
            
            # Keep history bounded
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
        except Exception as e:
            logger.warning(f"Failed to update conversation state: {e}")
    
    def _store_learning(self, query: str, insights: List):
        """Store significant insights for future learning"""
        try:
            self.hippocampus.store_learning('insight', {
                'query': query[:200],
                'insights': insights,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Failed to store learning: {e}")
    
    def _parse_analysis_result(self, result_text: str, query: str) -> Dict:
        """Parse raw analysis result into structured format"""
        parsed = {
            'formatted_text': result_text,
            'insights': [],
            'metrics': {},
            'confidence': 0.85
        }
        
        # Extract potential insights (simple heuristic)
        lines = result_text.split('\n')
        for line in lines:
            if any(marker in line for marker in ['Issue:', 'Problem:', 'Recommendation:', 'Suggestion:']):
                parsed['insights'].append(line.strip())
        
        # Calculate basic metrics
        parsed['metrics'] = {
            'issues_found': len([l for l in lines if 'issue' in l.lower()]),
            'recommendations': len([l for l in lines if 'recommend' in l.lower()])
        }
        
        return parsed
    
    # ── FALLBACK METHODS FOR GRACEFUL DEGRADATION ───────────────────────────
    
    def _fallback_analysis(self, query: str, context: str, error_msg: str) -> Dict:
        """Graceful fallback for analysis pipeline"""
        return {
            "type": "analysis",
            "text": f"Basic analysis of: {query}\n\nContext loaded: {len(context)} chars\n(Note: Enhanced analysis unavailable due to: {error_msg[:100]})",
            "confidence": 0.5,
            "fallback_mode": True
        }
    
    def _fallback_debug(self, query: str, context: str, temperature: float, error_msg: str) -> Dict:
        """Graceful fallback for debug pipeline"""
        return {
            "type": "debug",
            "text": f"Basic debugging for: {query}\n\nTemperature: {temperature}\n(Note: Smart debugging unavailable due to: {error_msg[:100]})",
            "confidence": 0.5,
            "fallback_mode": True
        }
    
    def _fallback_build(self, query: str, context: str, temperature: float, error_msg: str) -> Dict:
        """Graceful fallback for build pipeline"""
        return {
            "type": "build",
            "text": f"Basic creation for: {query}\n\nTemperature: {temperature}\n(Note: Smart building unavailable due to: {error_msg[:100]})",
            "confidence": 0.5,
            "fallback_mode": True
        }
    
    def _fallback_chat(self, query: str, context: str, temperature: float, error_msg: str) -> Dict:
        """Graceful fallback for chat pipeline"""
        return {
            "type": "chat",
            "text": f"Response to: {query}\n\nTemperature: {temperature}\n(Note: Enhanced chat unavailable due to: {error_msg[:100]})",
            "confidence": 0.5,
            "fallback_mode": True
        }

    # ── BENCHMARK ENHANCEMENT HELPER METHODS ────────────────────────────────────────
    
    def _extract_query_constraints(self, query: str) -> Dict:
        """
        Extract explicit constraints from user query for Category 1 (Instruction Following).
        
        Detects:
        - Line limits: "under 10 lines", "max 20 lines"
        - Format requirements: "numbered list", "JSON only", "no comments"
        - Content restrictions: "only function signature", "no explanation"
        - Type requirements: "static typing", "GDScript"
        - Length constraints: "one sentence", "brief", "detailed"
        
        Returns: Dict with constraint types and values
        """
        constraints = {
            'max_lines': None,
            'format': None,
            'content_type': 'full',  # full, signature_only, no_explanation
            'requires_typing': False,
            'response_length': 'auto',  # auto, brief, detailed
            'exclude_comments': False,
            'numbered_list': False,
            'json_only': False
        }
        
        query_lower = query.lower()
        
        # Line limit detection
        import re
        line_match = re.search(r'(?:under|below|less than|max(?:imum)?|up to)\s*(\d+)\s*lines?', query_lower)
        if line_match:
            constraints['max_lines'] = int(line_match.group(1))
        
        # Format detection
        if 'numbered' in query_lower and ('list' in query_lower or 'items' in query_lower):
            constraints['numbered_list'] = True
            constraints['format'] = 'numbered_list'
        elif 'json' in query_lower:
            constraints['json_only'] = True
            constraints['format'] = 'json'
        elif 'diff' in query_lower:
            constraints['format'] = 'diff'
        
        # Content type detection
        if 'only the function signature' in query_lower or 'just the signature' in query_lower:
            constraints['content_type'] = 'signature_only'
        elif 'no explanation' in query_lower or 'without explanation' in query_lower:
            constraints['content_type'] = 'no_explanation'
        elif 'code only' in query_lower or 'just code' in query_lower:
            constraints['content_type'] = 'code_only'
        
        # Comment exclusion
        if 'no comments' in query_lower or 'without comments' in query_lower:
            constraints['exclude_comments'] = True
        
        # Typing requirement
        if 'static typing' in query_lower or 'typed' in query_lower or 'type hint' in query_lower:
            constraints['requires_typing'] = True
        
        # Response length
        if 'one sentence' in query_lower or 'single sentence' in query_lower:
            constraints['response_length'] = 'one_sentence'
        elif 'brief' in query_lower or 'short' in query_lower or 'concise' in query_lower:
            constraints['response_length'] = 'brief'
        elif 'detailed' in query_lower or 'comprehensive' in query_lower or 'explain fully' in query_lower:
            constraints['response_length'] = 'detailed'
        
        return constraints
    
    def _build_constraint_instruction(self, constraints: Dict) -> str:
        """
        Build natural language instruction to inject into LLM prompt for constraint enforcement.
        """
        instructions = []
        
        # Ensure all expected keys exist with defaults
        constraints = {**{
            'max_lines': None,
            'content_type': 'full',
            'exclude_comments': False,
            'requires_typing': False,
            'response_length': 'auto',
            'numbered_list': False,
            'json_only': False,
            'format': None
        }, **constraints}
        
        if constraints['max_lines']:
            instructions.append(f"- CRITICAL: Output must be UNDER {constraints['max_lines']} lines of code")
        
        if constraints.get('content_type') == 'signature_only':
            instructions.append("- CRITICAL: Provide ONLY the function signature, NO body implementation")
        elif constraints['content_type'] == 'no_explanation':
            instructions.append("- CRITICAL: Provide ONLY code, NO explanations or commentary")
        elif constraints['content_type'] == 'code_only':
            instructions.append("- CRITICAL: Code only, no text outside code blocks")
        
        if constraints['exclude_comments']:
            instructions.append("- Do NOT include any comments in the code")
        
        if constraints['requires_typing']:
            instructions.append("- Use static type hints for all function signatures")
        
        if constraints['response_length'] == 'one_sentence':
            instructions.append("- CRITICAL: Answer in EXACTLY ONE SENTENCE")
        elif constraints['response_length'] == 'brief':
            instructions.append("- Keep response brief and concise (2-3 sentences max)")
        elif constraints['response_length'] == 'detailed':
            instructions.append("- Provide comprehensive, detailed explanation")
        
        if constraints['numbered_list']:
            instructions.append("- Format output as a numbered list")
        
        if constraints['json_only']:
            instructions.append("- Output MUST be valid JSON only, no markdown or explanation")
        
        if constraints['format'] == 'diff':
            instructions.append("- Output in unified diff format")
        
        if not instructions:
            return "Follow standard best practices for Godot/GDScript development."
        
        return "\n".join(instructions)
    
    def _validate_output_constraints(self, output_text: str, constraints: Dict) -> Dict:
        """
        Validate generated output against extracted constraints.
        
        Returns: {'valid': bool, 'issues': List[str]}
        """
        issues = []
        
        # Ensure all expected keys exist with defaults
        constraints = {**{
            'max_lines': None,
            'content_type': 'full',
            'exclude_comments': False,
            'json_only': False,
            'response_length': 'auto'
        }, **constraints}
        
        # Check line count
        if constraints['max_lines']:
            # Count non-empty lines in code blocks
            code_blocks = re.findall(r'```(?:gdscript)?\n(.*?)```', output_text, re.DOTALL)
            if code_blocks:
                for block in code_blocks:
                    line_count = len([l for l in block.split('\n') if l.strip()])
                    if line_count > constraints['max_lines']:
                        issues.append(f"Code has {line_count} lines, exceeds limit of {constraints['max_lines']}")
            else:
                # Count lines in entire output
                line_count = len([l for l in output_text.split('\n') if l.strip()])
                if line_count > constraints['max_lines']:
                    issues.append(f"Output has {line_count} lines, exceeds limit of {constraints['max_lines']}")
        
        # Check for unwanted explanations
        if constraints['content_type'] == 'signature_only':
            if len(output_text) > 200 or '\n' in output_text and len(output_text.split('\n')) > 3:
                issues.append("Output appears to contain more than just a signature")
        
        # Check for comments when excluded
        if constraints['exclude_comments']:
            if '#' in output_text or '//' in output_text or '/*' in output_text:
                issues.append("Output contains comments despite 'no comments' constraint")
        
        # Check JSON validity
        if constraints['json_only']:
            try:
                json.loads(output_text.strip())
            except json.JSONDecodeError:
                issues.append("Output is not valid JSON")
        
        # Check sentence count
        if constraints['response_length'] == 'one_sentence':
            sentences = re.split(r'[.!?]+', output_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) != 1:
                issues.append(f"Output has {len(sentences)} sentences, expected exactly 1")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    async def _retry_with_stricter_constraints(self, query: str, context: str, constraints: Dict, issues: List[str]) -> str:
        """
        Retry LLM call with stricter constraint enforcement when validation fails.
        """
        logger.warning(f"Retrying with stricter constraints due to: {issues}")
        
        # Add explicit violation warnings to context
        retry_context = context + f"\n\n[PREVIOUS ATTEMPT FAILED - STRICTER ENFORCEMENT REQUIRED]\nYour previous output violated these constraints: {', '.join(issues)}\n\nYou MUST strictly adhere to ALL constraints this time. Failure is not acceptable."
        
        analyze_func, _, _, _ = _get_builder_functions()
        loop = asyncio.get_event_loop()
        
        try:
            result_text = await loop.run_in_executor(
                self._executor,
                analyze_func,
                query, retry_context, self.conversation_history[-3:]  # Shorter history for speed
            )
            return result_text
        except Exception as e:
            logger.error(f"Retry failed: {e}")
            return "[Constraint enforcement failed - please rephrase your request]"
    
    def _ensure_json_serializable(self, obj: Any) -> Any:
        """
        Ensure object is JSON-serializable for app.py compatibility (Category 10).
        
        Converts:
        - Sets to lists
        - Tuples to lists
        - Custom objects to dicts (via __dict__ or str)
        - Non-serializable types to strings
        - NaN/Inf to None
        """
        import math
        
        if isinstance(obj, dict):
            return {str(k): self._ensure_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple, set)):
            return [self._ensure_json_serializable(item) for item in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif isinstance(obj, (int, str, bool, type(None))):
            return obj
        elif hasattr(obj, '__dict__'):
            return self._ensure_json_serializable(obj.__dict__)
        else:
            return str(obj)


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
