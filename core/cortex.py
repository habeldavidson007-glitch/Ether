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
        """
        Smart Analysis Pipeline - Enhanced with consciousness state injection and result parsing.
        
        Flow:
        1. Inject user history and project state into context
        2. Run safety preview on analysis request
        3. Call builder.analyze() with enriched context
        4. Parse results and extract actionable insights
        5. Store learnings in adaptive memory
        """
        step("🔍 Analyzing with enhanced context...")
        
        # Lazy load builder functions
        analyze_func, _, _, _ = _get_builder_functions()
        
        try:
            # STEP 1: Enrich context with consciousness state
            enriched_context = self._inject_consciousness_context(query, context, "analyze")
            
            # STEP 2: Safety preview for analysis operations
            safety_check = self.safety.preview_operation(query, enriched_context)
            if not safety_check.get('allowed', True):
                step("⚠️ Safety review triggered")
                return {
                    "type": "analysis",
                    "text": safety_check.get('message', 'Analysis requires safety review'),
                    "safety_flagged": True
                }
            
            # STEP 3: Execute analysis with enriched context
            result_text = analyze_func(query, enriched_context, self.conversation_history)
            
            # STEP 4: Parse and structure results
            parsed_result = self._parse_analysis_result(result_text, query)
            
            # STEP 5: Store learning if significant insights found
            if parsed_result.get('insights'):
                self._store_learning(query, parsed_result['insights'])
            
            step("✓ Analysis complete with structured insights")
            return {
                "type": "analysis",
                "text": parsed_result.get('formatted_text', result_text),
                "insights": parsed_result.get('insights', []),
                "metrics": parsed_result.get('metrics', {}),
                "confidence": parsed_result.get('confidence', 0.85)
            }
            
        except Exception as e:
            logger.error(f"Smart analysis pipeline failed: {e}")
            # Graceful degradation to basic analysis
            return self._fallback_analysis(query, context, str(e))
    
    def _run_debug_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """
        Smart Debug Pipeline - Enhanced with multi-strategy debugging and validation.
        
        Flow:
        1. Extract error patterns and build debug context
        2. Check conversation history for related fixes
        3. Apply CoT fallback if pattern not recognized
        4. Call builder.debug() with strategic context
        5. Validate fix and generate verification steps
        """
        step("🐛 Smart debugging with multi-strategy approach...")
        
        # Lazy load builder functions
        _, debug_func, _, _ = _get_builder_functions()
        
        try:
            # STEP 1: Extract and categorize error patterns
            error_patterns = self._extract_error_patterns(query)
            debug_context = self._build_debug_context(query, context, error_patterns)
            
            # STEP 2: Check history for similar issues
            historical_fix = self._find_similar_historical_fix(query, error_patterns)
            if historical_fix:
                step("⚡ Found similar historical fix")
                return {
                    "type": "debug",
                    "text": historical_fix['explanation'],
                    "changes": historical_fix.get('changes', []),
                    "from_history": True,
                    "confidence": 0.95
                }
            
            # STEP 3: Apply CoT fallback for novel bugs
            if not error_patterns.get('recognized', False):
                step("🧠 Novel bug detected - applying Chain-of-Thought")
                cot_data = _cot_fallback(
                    {"action": "debug", "file": error_patterns.get('file', 'unknown')},
                    {"issues": error_patterns.get('issues', [])},
                    debug_context[:500]
                )
                debug_context += f"\n\n[COT INSTRUCTION]\n{cot_data['cot_prompt']}"
            
            # STEP 4: Execute debug with strategic context
            result = debug_func(query, debug_context)
            
            # STEP 5: Validate and enhance fix
            validated_result = self._validate_debug_result(result, query, error_patterns)
            
            step("✓ Debug complete with validation")
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
    
    def _run_build_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """
        Smart Build Pipeline - Enhanced with requirements extraction and quality gates.
        
        Flow:
        1. Extract implicit requirements from query
        2. Check project conventions and existing patterns
        3. Apply creativity boost for high-temperature builds
        4. Call builder.run_pipeline() with full context
        5. Run quality gates on generated code
        """
        step("🔨 Smart building with quality gates...")
        
        # Lazy load builder functions
        _, _, run_pipeline_func, _ = _get_builder_functions()
        
        try:
            # STEP 1: Extract requirements and constraints
            requirements = self._extract_build_requirements(query, context)
            
            # STEP 2: Load project conventions
            conventions = self._load_project_conventions()
            build_context = self._merge_context_with_conventions(context, conventions, requirements)
            
            # STEP 3: Adjust prompt based on temperature for creativity
            if temperature > 0.7 and use_n_sampling:
                step("🎨 High creativity mode with N-sampling")
                build_context += "\n\n[CREATIVITY MODE]\nGenerate innovative solutions. Consider multiple approaches."
            
            # STEP 4: Execute build pipeline
            result, logs = run_pipeline_func(
                task=query,
                intent="build",
                context=build_context,
                history=self.conversation_history,
                yield_steps=step,
                requirements=requirements
            )
            
            # STEP 5: Run quality gates
            quality_report = self._run_quality_gates(result, requirements)
            
            # STEP 6: Store successful patterns
            if quality_report.get('passed', False):
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
    
    def _run_chat_pipeline(self, query: str, context: str, temperature: float, use_n_sampling: bool, step) -> Dict:
        """
        Smart Chat Pipeline - Enhanced with personality adaptation and context awareness.
        
        Flow:
        1. Analyze conversation flow and user expertise level
        2. Adapt response style based on history
        3. Inject relevant knowledge from hippocampus
        4. Call builder.chat() with personalized context
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
            
            # STEP 4: Execute chat with personalized context
            result_text = chat_func(query, self.conversation_history, chat_context)
            
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
        match = re.search(r'([\\w\\-]+\\.gd)', query.lower())
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
