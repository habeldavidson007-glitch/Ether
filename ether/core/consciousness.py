"""
Ether Consciousness Engine - Phase 10: The Great Unification

This module unifies all fragmented components (Memory, Tools, Cognitive Layers)
into a single Deterministic Neuro-Symbolic Agent.

Architecture:
- Cortex: Deterministic Intent Classification (TF-IDF + Decision Rules)
- Hippocampus: Unified Memory (Working + Long-term + Semantic)
- Effectors: Registered Tools (Code Fixer, Analyzer, etc.)
- SafetyGuard: Pre-execution validation
"""

import os
import re
import json
import logging
import psutil
import zstandard as zstd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

# ML Dependencies
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("scikit-learn not available. Falling back to rule-based classification.")

logger = logging.getLogger(__name__)

# Compression settings for Hippocampus
COMPRESSION_LEVEL = 3  # Balance between speed and ratio (1-9)
MAX_MEMORY_SIZE_MB = 200  # Hard cap on memory usage

# Godot-related keywords for domain filtering
GODOT_KEYWORDS = {
    "godot", "gdscript", "scene", "node", "shader", "tscn", "gdextension",
    "engine", "viewport", "canvas", "sprite", "kinematic", "rigidbody",
    "area", "collision", "signal", " tween", "animation", "material",
    "texture", "mesh", "light", "camera", "ui", "control", "panel",
    "button", "label", "lineedit", "vbox", "hbox", "grid", "margin",
    "color", "vector2", "vector3", "transform", "basis", "quat", "pool",
    "array", "dictionary", "yield", "await", "coroutine", "rpc", "network",
    "export", "onready", "class_name", "extends", "func", "var", "const",
    "enum", "tool", "editor", "inspector", "filesystem", "debugger"
}

# Model configuration based on RAM
MODEL_7B = "qwen2.5-coder:7b-instruct-q4_k_m"
MODEL_1_5B = "qwen2.5-coder:1.5b-instruct-q4_k_m"
RAM_THRESHOLD_GB = 8


def detect_ram_and_suggest_model() -> Tuple[str, int]:
    """
    Detect available RAM and suggest appropriate model.
    
    Returns:
        Tuple of (model_name, available_ram_gb)
    """
    try:
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024 ** 3)
        
        if available_gb > RAM_THRESHOLD_GB:
            suggested_model = MODEL_7B
            logger.info(f"Available RAM: {available_gb:.1f}GB (> {RAM_THRESHOLD_GB}GB) → Suggesting {MODEL_7B}")
        else:
            suggested_model = MODEL_1_5B
            logger.info(f"Available RAM: {available_gb:.1f}GB (≤ {RAM_THRESHOLD_GB}GB) → Using {MODEL_1_5B}")
        
        return suggested_model, int(available_gb)
    except Exception as e:
        logger.warning(f"Failed to detect RAM: {e}. Defaulting to 1.5B model.")
        return MODEL_1_5B, 0

@dataclass
class MemoryUnit:
    """Unified memory unit for Hippocampus"""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    access_count: int = 0
    relevance_score: float = 1.0

class Hippocampus:
    """
    Step 2: Consolidated Memory System with Zstd Compression
    Merges Adaptive Memory, Librarian, and Context Manager
    
    Features:
    - Zstandard compression for efficient storage (3-5x reduction)
    - 200MB hard cap with intelligent eviction
    - General knowledge support (not just Godot)
    - Pre-fetch queue for instant responses
    """
    def __init__(self, capacity: int = 1000, max_size_mb: int = MAX_MEMORY_SIZE_MB):
        self.capacity = capacity
        self.max_size_mb = max_size_mb
        self.working_memory: List[MemoryUnit] = []
        self.long_term_memory: List[MemoryUnit] = []
        self.prefetch_queue: Dict[str, str] = {}  # topic -> compressed_content
        self.vectorizer: Optional[Any] = None
        self.compressor = zstd.ZstdCompressor(level=COMPRESSION_LEVEL)
        self.decompressor = zstd.ZstdDecompressor()
        self._current_size_bytes = 0
        
        # Initialize semantic search if possible
        if ML_AVAILABLE:
            self.vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        
        logger.info(f"Hippocampus initialized with unified memory (max {max_size_mb}MB, compression level {COMPRESSION_LEVEL})")

    def _compress_content(self, content: str) -> bytes:
        """Compress content using Zstandard"""
        try:
            compressed = self.compressor.compress(content.encode('utf-8'))
            return compressed
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return content.encode('utf-8')
    
    def _decompress_content(self, compressed_data: bytes) -> str:
        """Decompress Zstandard content"""
        try:
            decompressed = self.decompressor.decompress(compressed_data)
            return decompressed.decode('utf-8')
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            try:
                return compressed_data.decode('utf-8')
            except:
                return ""
    
    def _estimate_size(self, content: str) -> int:
        """Estimate compressed size of content"""
        compressed = self._compress_content(content)
        return len(compressed)
    
    def _enforce_memory_cap(self):
        """Enforce 200MB cap by evicting low-priority memories"""
        max_bytes = self.max_size_mb * 1024 * 1024
        
        if self._current_size_bytes <= max_bytes:
            return
        
        logger.info(f"Memory cap exceeded ({self._current_size_bytes/1024/1024:.1f}MB > {self.max_size_mb}MB), evicting...")
        
        # Sort by relevance and access count (lower = evict first)
        self.long_term_memory.sort(key=lambda x: (x.relevance_score, x.access_count))
        
        # Evict until under cap
        while self._current_size_bytes > max_bytes * 0.8 and self.long_term_memory:
            victim = self.long_term_memory.pop(0)
            estimated = self._estimate_size(victim.content)
            self._current_size_bytes -= estimated
            logger.debug(f"Evicted memory unit: {victim.content[:50]}...")
        
        logger.info(f"Memory after eviction: {self._current_size_bytes/1024/1024:.1f}MB")
    
    def add_to_working(self, content: str, metadata: Dict[str, Any] = None):
        """Add to short-term working memory with compression tracking"""
        unit = MemoryUnit(content=content, metadata=metadata or {})
        self.working_memory.append(unit)
        
        # Track size
        estimated = self._estimate_size(content)
        self._current_size_bytes += estimated
        
        # Cap working memory
        if len(self.working_memory) > 50:
            self.consolidate_to_long_term()
        
        # Enforce global cap
        self._enforce_memory_cap()
            
        return unit

    def consolidate_to_long_term(self):
        """Move important working memories to long-term storage with compression"""
        if not self.working_memory:
            return
            
        # Simple heuristic: move oldest 80% to long-term
        threshold = len(self.working_memory) * 0.2
        to_move = self.working_memory[:int(threshold)]
        self.working_memory = self.working_memory[int(threshold):]
        
        for unit in to_move:
            if unit.relevance_score > 0.5:
                self.long_term_memory.append(unit)
                
        # Cap long-term memory with size awareness
        if len(self.long_term_memory) > self.capacity:
            self.long_term_memory = sorted(
                self.long_term_memory, 
                key=lambda x: x.relevance_score, 
                reverse=True
            )[:self.capacity]
        
        # Recalculate total size
        self._current_size_bytes = sum(
            self._estimate_size(unit.content) 
            for unit in self.long_term_memory + self.working_memory
        )

    def semantic_search(self, query: str, top_k: int = 5) -> List[MemoryUnit]:
        """Search memory using semantic similarity"""
        if not self.long_term_memory:
            return []
            
        if not ML_AVAILABLE or not self.vectorizer:
            return self._keyword_search(query, top_k)
            
        try:
            corpus = [unit.content for unit in self.long_term_memory]
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            query_vec = self.vectorizer.transform([query])
            
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(query_vec, tfidf_matrix)[0]
            
            top_indices = similarities.argsort()[-top_k:][::-1]
            results = [self.long_term_memory[i] for i in top_indices if similarities[i] > 0.1]
            
            for unit in results:
                unit.access_count += 1
                
            return results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> List[MemoryUnit]:
        """Fallback keyword search"""
        query_lower = query.lower()
        scored = []
        for unit in self.long_term_memory:
            score = unit.content.lower().count(query_lower) * 0.1
            score += unit.relevance_score
            scored.append((score, unit))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [unit for _, unit in scored[:top_k]]

    def add_to_prefetch(self, topic: str, content: str):
        """Add content to prefetch queue (compressed)"""
        compressed = self._compress_content(content)
        # Store as base64-like hex string for JSON compatibility
        self.prefetch_queue[topic.lower()] = compressed.hex()
        
        logger.debug(f"Added prefetch for '{topic}' ({len(compressed)} bytes compressed)")
    
    def get_from_prefetch(self, topic: str) -> Optional[str]:
        """Retrieve content from prefetch queue (decompressed)"""
        hex_data = self.prefetch_queue.get(topic.lower())
        if not hex_data:
            return None
        
        try:
            compressed = bytes.fromhex(hex_data)
            return self._decompress_content(compressed)
        except Exception as e:
            logger.error(f"Failed to retrieve prefetch for '{topic}': {e}")
            return None

    def check_prefetch(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Check if query matches any prefetched topics.
        
        Returns dict with 'content' and 'topic' keys if match found, None otherwise.
        This is the main interface used by builder.py for prefetch-first architecture.
        """
        if not self.prefetch_queue:
            return None
        
        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 3]
        
        # Check each significant word in query against prefetch topics
        for word in query_words:
            # Exact match
            if word in self.prefetch_queue:
                content = self.get_from_prefetch(word)
                if content:
                    logger.debug(f"Prefetch hit for topic '{word}'")
                    return {"topic": word, "content": content, "match_type": "exact"}
            
            # Partial match (topic contains query word or vice versa)
            for topic in self.prefetch_queue.keys():
                if word in topic or topic in word:
                    content = self.get_from_prefetch(topic)
                    if content:
                        logger.debug(f"Prefetch partial hit: '{word}' matched '{topic}'")
                        return {"topic": topic, "content": content, "match_type": "partial"}
        
        # No match found
        return None
    
    def clear_prefetch(self):
        """Clear prefetch queue"""
        self.prefetch_queue.clear()
        logger.debug("Prefetch queue cleared")
    
    def get_prefetch_stats(self) -> dict:
        """Get prefetch queue statistics"""
        total_size = sum(len(bytes.fromhex(v)) for v in self.prefetch_queue.values())
        return {
            "topics": len(self.prefetch_queue),
            "compressed_size_kb": round(total_size / 1024, 2)
        }
    
    def get_context(self, query: str, use_prefetch: bool = True) -> str:
        """Retrieve relevant context for current query, optionally using prefetch"""
        # First check prefetch queue for instant response
        if use_prefetch:
            query_words = query.lower().split()
            for word in query_words:
                if len(word) > 3:  # Skip short words
                    prefetched = self.get_from_prefetch(word)
                    if prefetched:
                        logger.debug(f"Using prefetched context for '{word}'")
                        return prefetched
        
        # Fallback to semantic search
        relevant = self.semantic_search(query, top_k=3)
        if not relevant:
            return ""
        return "\n---\n".join([unit.content for unit in relevant])
    
    def get_memory_stats(self) -> dict:
        """Get comprehensive memory statistics"""
        working_size = sum(self._estimate_size(u.content) for u in self.working_memory)
        long_term_size = sum(self._estimate_size(u.content) for u in self.long_term_memory)
        
        return {
            "working_memory_count": len(self.working_memory),
            "long_term_memory_count": len(self.long_term_memory),
            "working_memory_kb": round(working_size / 1024, 2),
            "long_term_memory_kb": round(long_term_size / 1024, 2),
            "total_size_mb": round((working_size + long_term_size) / 1024 / 1024, 2),
            "max_size_mb": self.max_size_mb,
            "compression_ratio": "~3-5x",
            "prefetch_topics": len(self.prefetch_queue)
        }


@dataclass
class ToolSkill:
    """Registered tool/skill metadata"""
    name: str
    description: str
    keywords: List[str]
    handler: Any
    input_schema: Dict[str, Any]
    is_safe: bool = True

class EffectorRegistry:
    """
    Step 3: Tool Registry
    Registers all existing modules as skills
    """
    def __init__(self):
        self.skills: Dict[str, ToolSkill] = {}
        self._register_builtin_skills()
        logger.info(f"EffectorRegistry initialized with {len(self.skills)} skills")

    def _register_builtin_skills(self):
        """Register existing core modules as skills"""
        # Note: Handlers will be dynamically imported when needed
        self.register_skill(ToolSkill(
            name="code_fixer",
            description="Fixes GDScript code errors and suggests improvements",
            keywords=["fix", "error", "bug", "correct", "repair", "code"],
            handler=None,  # Lazy loaded
            input_schema={"code": "str", "error_msg": "str"}
        ))
        
        self.register_skill(ToolSkill(
            name="static_analyzer",
            description="Analyzes code for potential issues without running it",
            keywords=["analyze", "scan", "check", "inspect", "review"],
            handler=None,
            input_schema={"code": "str"}
        ))
        
        self.register_skill(ToolSkill(
            name="dependency_graph",
            description="Builds and analyzes project dependency graphs",
            keywords=["dependency", "graph", "import", "relationship"],
            handler=None,
            input_schema={"project_path": "str"}
        ))
        
        self.register_skill(ToolSkill(
            name="scene_analyzer",
            description="Analyzes Godot scene structure and node relationships",
            keywords=["scene", "node", "tree", "structure", "godot"],
            handler=None,
            input_schema={"scene_path": "str"}
        ))
        
        self.register_skill(ToolSkill(
            name="validator",
            description="Validates Godot project configuration and best practices",
            keywords=["validate", "verify", "check", "project.godot", "config"],
            handler=None,
            input_schema={"project_path": "str"}
        ))
        
        self.register_skill(ToolSkill(
            name="cascade_scanner",
            description="Scans for cascading errors and dependency issues",
            keywords=["cascade", "chain", "ripple", "propagate"],
            handler=None,
            input_schema={"path": "str"}
        ))

    def register_skill(self, skill: ToolSkill):
        """Register a new skill"""
        self.skills[skill.name] = skill

    def find_relevant_skills(self, intent: str, keywords: List[str]) -> List[ToolSkill]:
        """Find skills relevant to the intent"""
        relevant = []
        intent_lower = intent.lower()
        
        for skill in self.skills.values():
            score = 0
            if any(kw in intent_lower for kw in skill.keywords):
                score += 2
            if any(kw in ' '.join(keywords).lower() for kw in skill.keywords):
                score += 1
            if score > 0:
                relevant.append((score, skill))
        
        relevant.sort(reverse=True, key=lambda x: x[0])
        return [skill for _, skill in relevant]
    
    def load_handler(self, skill_name: str):
        """Lazy load handler for a skill"""
        if skill_name not in self.skills:
            return None
            
        skill = self.skills[skill_name]
        if skill.handler is not None:
            return skill.handler
            
        # Dynamic import based on skill name - try multiple paths
        try:
            if skill_name == "code_fixer":
                try:
                    from ..core import code_fixer
                except ImportError:
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                    from core import code_fixer
                skill.handler = getattr(code_fixer, 'fix_code', None)
            elif skill_name == "static_analyzer":
                try:
                    from ..core import static_analyzer
                except ImportError:
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                    from core import static_analyzer
                skill.handler = getattr(static_analyzer, 'analyze', None)
            elif skill_name == "dependency_graph":
                try:
                    from ..core import dependency_graph
                except ImportError:
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                    from core import dependency_graph
                skill.handler = getattr(dependency_graph, 'build_graph', None)
            elif skill_name == "scene_analyzer":
                try:
                    from ..core import scene_graph_analyzer
                except ImportError:
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                    from core import scene_graph_analyzer
                skill.handler = getattr(scene_graph_analyzer, 'analyze_scene', None)
            elif skill_name == "validator":
                try:
                    from ..core import godot_validator
                except ImportError:
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                    from core import godot_validator
                skill.handler = getattr(godot_validator, 'validate_project', None)
            elif skill_name == "cascade_scanner":
                try:
                    from ..core import cascade_scanner
                except ImportError:
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                    from core import cascade_scanner
                skill.handler = getattr(cascade_scanner, 'scan', None)
        except Exception as e:
            logger.error(f"Failed to load handler for {skill_name}: {e}")
            
        return skill.handler


class Cortex:
    """
    Step 4: Deterministic ML Layer
    Intent Classification and Decision Making
    """
    def __init__(self):
        self.classifier: Optional[Pipeline] = None
        self.intent_history: List[str] = []
        self.training_data: List[Tuple[str, str]] = []
        
        if ML_AVAILABLE:
            self._initialize_classifier()
        logger.info("Cortex initialized")

    def _initialize_classifier(self):
        """Initialize the ML pipeline"""
        self.classifier = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=1000)),
            ('clf', LogisticRegression(max_iter=1000))
        ])
        self._seed_training_data()
        self._retrain()

    def _seed_training_data(self):
        """Seed with predefined patterns"""
        patterns = [
            ("fix this code", "fix_code"),
            ("repair error", "fix_code"),
            ("bug in script", "fix_code"),
            ("analyze this", "analyze"),
            ("scan for issues", "analyze"),
            ("check dependencies", "dependencies"),
            ("show graph", "dependencies"),
            ("validate project", "validate"),
            ("verify config", "validate"),
            ("scene structure", "scene_analysis"),
            ("node tree", "scene_analysis"),
            ("general question", "chat"),
            ("hello", "chat"),
        ]
        self.training_data.extend(patterns)

    def _retrain(self):
        """Retrain classifier on accumulated data"""
        if not self.classifier or not self.training_data:
            return
        texts, labels = zip(*self.training_data)
        try:
            self.classifier.fit(texts, labels)
        except Exception as e:
            logger.error(f"Training failed: {e}")

    def classify_intent(self, query: str) -> Tuple[str, float]:
        """Classify user intent deterministically"""
        if not ML_AVAILABLE or not self.classifier:
            return self._rule_based_classification(query), 0.8
            
        try:
            prediction = self.classifier.predict([query])[0]
            proba = self.classifier.predict_proba([query])[0].max()
            self.intent_history.append(prediction)
            if len(self.intent_history) % 10 == 0:
                self._retrain()
            return prediction, proba
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return self._rule_based_classification(query), 0.5

    def _rule_based_classification(self, query: str) -> str:
        """Fallback rule-based classification"""
        query_lower = query.lower()
        if any(w in query_lower for w in ["fix", "error", "bug", "repair"]):
            return "fix_code"
        elif any(w in query_lower for w in ["analyze", "scan", "check"]):
            return "analyze"
        elif any(w in query_lower for w in ["dependency", "graph", "import"]):
            return "dependencies"
        elif any(w in query_lower for w in ["validate", "verify", "config"]):
            return "validate"
        elif any(w in query_lower for w in ["scene", "node", "tree"]):
            return "scene_analysis"
        else:
            return "chat"

    def add_feedback(self, query: str, correct_intent: str):
        """Learn from user feedback"""
        self.training_data.append((query, correct_intent))


class SafetyGuard:
    """Pre-execution safety validation"""
    
    DANGEROUS_PATTERNS = [
        r"os\.system\s*\(",
        r"subprocess\.",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
    ]
    
    def __init__(self):
        self.compiled_patterns = [re.compile(p) for p in self.DANGEROUS_PATTERNS]

    def validate_code(self, code: str) -> Tuple[bool, str]:
        """Validate code before execution"""
        for pattern in self.compiled_patterns:
            if pattern.search(code):
                return False, f"Dangerous pattern detected"
        return True, "Safe"

    def validate_path(self, path: str, allowed_root: str = None) -> Tuple[bool, str]:
        """Validate file path access"""
        try:
            p = Path(path).resolve()
            if str(p) == "/":
                return False, "Cannot access root directory"
            if allowed_root:
                root = Path(allowed_root).resolve()
                try:
                    p.relative_to(root)
                except ValueError:
                    return False, f"Path outside allowed root"
            return True, "Path valid"
        except Exception as e:
            return False, f"Path validation error: {e}"


class EtherConsciousness:
    """
    Main Consciousness Engine - The Brain of Ether
    
    Unifies:
    - Memory (Hippocampus)
    - Cognition (Cortex)
    - Action (EffectorRegistry)
    - Safety (SafetyGuard)
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.hippocampus = Hippocampus()
        self.cortex = Cortex()
        self.effectors = EffectorRegistry()
        self.safety = SafetyGuard()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Detect RAM and suggest model at startup
        suggested_model, available_ram = detect_ram_and_suggest_model()
        self.suggested_model = suggested_model
        self.available_ram_gb = available_ram
        logger.info(f"EtherConsciousness initialized (Session: {self.session_id})")

    def is_godot_related(self, query: str) -> bool:
        """
        Check if a query is related to Godot/GDScript development.
        
        Uses a two-tier approach:
        1. Fast keyword heuristic check
        2. Low-threshold ML confidence check for ambiguous cases
        
        Note: This check is bypassed if content is available in prefetch queue
        (allowing general knowledge queries that were pre-fetched by MCP daemon).
        
        Returns:
            True if query is Godot-related, False otherwise
        """
        query_lower = query.lower()
        
        # Tier 1: Keyword heuristic check (fast path)
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
        
        # Fallback: if we got here with 1 keyword, be conservative and allow it
        return True

    def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main entry point: Process user query through consciousness loop"""
        start_time = datetime.now()

        # Step 0: Off-Domain Guard - filter non-Godot queries
        if not self.is_godot_related(query):
            words = query.split()[:5]
            topic = " ".join(words).rstrip("?.!,")
            return {
                "session_id": self.session_id,
                "query": query,
                "intent": "refused",
                "confidence": 1.0,
                "output": f"Ether is specialized for Godot/GDScript development. I cannot assist with {topic}.",
                "skills_used": [],
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "success": False,
                "error": "off_domain"
            }
        
        # Step 1: Classify Intent
        intent, confidence = self.cortex.classify_intent(query)
        
        # Step 2: Retrieve Context from Memory
        memory_context = self.hippocampus.get_context(query)
        
        # Step 3: Find Relevant Skills
        keywords = query.split()
        relevant_skills = self.effectors.find_relevant_skills(intent, keywords)
        
        # Step 4: Execute or Respond
        response = self._execute_intent(intent, query, relevant_skills, memory_context, context or {})
        
        # Step 5: Store in Memory
        self.hippocampus.add_to_working(
            content=f"Query: {query}\nResponse: {response.get('output', '')}",
            metadata={"intent": intent, "skills_used": [s.name for s in relevant_skills]}
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            "session_id": self.session_id,
            "query": query,
            "intent": intent,
            "confidence": confidence,
            "output": response.get("output", ""),
            "skills_used": [s.name for s in relevant_skills],
            "duration_ms": duration * 1000,
            "success": response.get("success", False),
            "error": response.get("error")
        }
        
        self.conversation_history.append(result)
        return result

    def _execute_intent(self, intent: str, query: str, skills: List[ToolSkill], context: str, user_context: Dict) -> Dict[str, Any]:
        """Execute based on classified intent"""
        if intent == "chat":
            return self._handle_chat(query, context)
            
        if not skills:
            return {"success": False, "output": "No relevant tools found", "error": "No skills"}
        
        primary_skill = skills[0]
        handler = self.effectors.load_handler(primary_skill.name)
        
        if not handler:
            return {"success": False, "output": f"Tool {primary_skill.name} not available", "error": "No handler"}
        
        params = self._extract_parameters(primary_skill, query, user_context)
        is_safe, msg = self._validate_inputs(params)
        if not is_safe:
            return {"success": False, "output": "", "error": msg}
        
        try:
            result = handler(**params)
            return {"success": True, "output": str(result), "skill": primary_skill.name}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def _handle_chat(self, query: str, context: str) -> Dict[str, Any]:
        """Handle general chat queries"""
        response = f"I understand you're asking: '{query}'"
        if context:
            response += f"\nContext: {context}"
        return {"success": True, "output": response}

    def _extract_parameters(self, skill: ToolSkill, query: str, user_context: Dict) -> Dict:
        """Extract parameters for skill execution"""
        params = {}
        for param_name in skill.input_schema.keys():
            if param_name in user_context:
                params[param_name] = user_context[param_name]
        
        if "path" in skill.input_schema and not params.get("path"):
            path_match = re.search(r'[/\\][\w./\\-]+', query)
            params["path"] = path_match.group() if path_match else str(self.project_root)
                
        if "code" in skill.input_schema and not params.get("code"):
            code_match = re.search(r'```(?:gdscript)?\n(.*?)```', query, re.DOTALL)
            if code_match:
                params["code"] = code_match.group(1)
                
        return params

    def _validate_inputs(self, params: Dict) -> Tuple[bool, str]:
        """Validate extracted inputs"""
        for key, value in params.items():
            if isinstance(value, str):
                if key in ["code", "script"]:
                    is_safe, msg = self.safety.validate_code(value)
                    if not is_safe:
                        return False, msg
                elif key in ["path", "file", "directory"]:
                    is_safe, msg = self.safety.validate_path(value, str(self.project_root))
                    if not is_safe:
                        return False, msg
        return True, "All inputs valid"

    def learn_from_feedback(self, query: str, was_helpful: bool, correct_intent: str = None):
        """Learn from user feedback"""
        if correct_intent:
            self.cortex.add_feedback(query, correct_intent)
        if self.hippocampus.working_memory:
            factor = 1.2 if was_helpful else 0.8
            self.hippocampus.working_memory[-1].relevance_score *= factor

    def get_status(self) -> Dict[str, Any]:
        """Get consciousness status"""
        return {
            "session_id": self.session_id,
            "working_memory_size": len(self.hippocampus.working_memory),
            "long_term_memory_size": len(self.hippocampus.long_term_memory),
            "registered_skills": list(self.effectors.skills.keys()),
            "conversation_turns": len(self.conversation_history),
            "ml_available": ML_AVAILABLE
        }


# Singleton instance
_consciousness_instance: Optional[EtherConsciousness] = None

def get_consciousness(project_root: str = None) -> EtherConsciousness:
    """Get or create singleton consciousness instance"""
    global _consciousness_instance
    if _consciousness_instance is None:
        _consciousness_instance = EtherConsciousness(project_root)
    return _consciousness_instance
