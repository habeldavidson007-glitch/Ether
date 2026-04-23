"""
Ether Consciousness Module - Neural Architecture for Ether v1.9.8
===================================================================

This module provides the neural architecture components for Ether:
- Hippocampus: Memory and prefetch queue system
- Cortex: Intent classification with ML fallback
- SafetyGuard: Content safety filtering
- EffectorRegistry: Action registration and execution

These components are used by cortex.py for unified brain functionality.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ── ML AVAILABILITY CHECK ─────────────────────────────────────────────────────
ML_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    ML_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn not available - using rule-based intent detection")

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
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

COMPRESSION_LEVEL = 6  # Zstd compression level
MAX_MEMORY_SIZE_MB = 200  # Maximum memory size in MB


# ── RAM DETECTION ─────────────────────────────────────────────────────────────
def detect_ram_and_suggest_model() -> Tuple[str, float]:
    """
    Detect available RAM and suggest appropriate Ollama model.
    
    Returns: (suggested_model, available_ram_gb)
    """
    try:
        import psutil
        total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        # Fallback for systems without psutil
        total_ram_gb = 4.0  # Assume 4GB default
    except Exception:
        total_ram_gb = 2.0  # Conservative fallback
    
    if total_ram_gb < 3:
        return "qwen2.5-coder:1.5b", total_ram_gb
    elif total_ram_gb < 6:
        return "qwen2.5-coder:3b", total_ram_gb
    else:
        return "qwen2.5-coder:7b", total_ram_gb


# ── MEMORY UNIT ───────────────────────────────────────────────────────────────
class MemoryUnit:
    """Represents a single memory unit in the Hippocampus."""
    
    def __init__(self, content: str, intent: str = "general", 
                 timestamp: float = None, priority: int = 1):
        self.content = content
        self.intent = intent
        self.timestamp = timestamp or datetime.now().timestamp()
        self.priority = priority
        self.access_count = 0
        self.last_accessed = self.timestamp
    
    def access(self):
        """Mark this memory as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now().timestamp()
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "intent": self.intent,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryUnit":
        unit = cls(
            content=data["content"],
            intent=data.get("intent", "general"),
            timestamp=data.get("timestamp"),
            priority=data.get("priority", 1)
        )
        unit.access_count = data.get("access_count", 0)
        unit.last_accessed = data.get("last_accessed", unit.timestamp)
        return unit


# ── HIPPOCAMPUS (Memory & Prefetch System) ────────────────────────────────────
class Hippocampus:
    """
    Hippocampus - Memory and Prefetch Queue System
    
    Manages:
    - Short-term conversation memory
    - Prefetch queue for general knowledge
    - LRU eviction based on access patterns
    """
    
    def __init__(self, max_size_mb: int = MAX_MEMORY_SIZE_MB):
        self.max_size_mb = max_size_mb
        self.memories: Dict[str, MemoryUnit] = {}
        self.prefetch_queue: Dict[str, str] = {}  # topic -> content
        self.total_size_bytes = 0
        
        logger.info(f"Hippocampus initialized with {max_size_mb}MB capacity")
    
    def store(self, key: str, content: str, intent: str = "general", 
              priority: int = 1) -> bool:
        """Store a memory unit."""
        try:
            content_bytes = len(content.encode('utf-8'))
            
            # Evict if necessary
            while self.total_size_bytes + content_bytes > self.max_size_mb * 1024 * 1024:
                self._evict_lru()
            
            unit = MemoryUnit(content, intent, priority=priority)
            self.memories[key] = unit
            self.total_size_bytes += content_bytes
            
            logger.debug(f"Stored memory '{key}' ({content_bytes} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False
    
    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve a memory by key."""
        if key in self.memories:
            unit = self.memories[key]
            unit.access()
            return unit.content
        return None
    
    def check_prefetch(self, query: str) -> Optional[Dict]:
        """
        Check if query matches any prefetched knowledge.
        
        Returns: {"topic": str, "content": str} or None
        """
        query_lower = query.lower()
        
        for topic, content in self.prefetch_queue.items():
            if topic in query_lower:
                return {"topic": topic, "content": content}
        
        return None
    
    def add_to_prefetch(self, topic: str, content: str):
        """Add content to prefetch queue."""
        self.prefetch_queue[topic] = content
        logger.debug(f"Added '{topic}' to prefetch queue")
    
    def _evict_lru(self):
        """Evict least recently used memory."""
        if not self.memories:
            return
        
        # Find LRU memory
        lru_key = min(
            self.memories.keys(),
            key=lambda k: (self.memories[k].access_count, self.memories[k].last_accessed)
        )
        
        unit = self.memories.pop(lru_key)
        self.total_size_bytes -= len(unit.content.encode('utf-8'))
        logger.debug(f"Evicted LRU memory '{lru_key}'")
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history."""
        sorted_memories = sorted(
            self.memories.values(),
            key=lambda m: m.last_accessed,
            reverse=True
        )[:limit]
        
        return [m.to_dict() for m in sorted_memories]
    
    def clear(self):
        """Clear all memories and prefetch queue."""
        self.memories.clear()
        self.prefetch_queue.clear()
        self.total_size_bytes = 0


# ── CORTEX (Intent Classification) ────────────────────────────────────────────
class Cortex:
    """
    Cortex - Intent Classification Engine
    
    Uses ML when available, falls back to rule-based detection otherwise.
    """
    
    def __init__(self):
        self.classifier = None
        self.trained = False
        self.fallback_patterns = self._build_fallback_patterns()
        
        if ML_AVAILABLE:
            logger.info("ML-based intent classification available")
        else:
            logger.info("Using rule-based intent classification")
    
    def _build_fallback_patterns(self) -> Dict[str, List[str]]:
        """Build regex patterns for fallback intent detection."""
        return {
            "debug": [
                r"error", r"bug", r"broken", r"crash", r"fail", r"fix",
                r"exception", r"traceback", r"not working", r"wrong"
            ],
            "explain": [
                r"what is", r"how does", r"why", r"explain", r"define",
                r"meaning", r"understand"
            ],
            "create": [
                r"create", r"make", r"build", r"implement", r"write",
                r"generate", r"add", r"new"
            ],
            "optimize": [
                r"optimize", r"improve", r"refactor", r"faster", r"better",
                r"efficient", r"performance"
            ],
            "analyze": [
                r"analyze", r"review", r"check", r"examine", r"inspect"
            ]
        }
    
    def train_from_logs(self, log_path: str = "logs/conversations.jsonl") -> bool:
        """
        Train classifier from conversation logs.
        
        Args:
            log_path: Path to JSONL file with labeled conversations
            
        Returns:
            True if training succeeded, False otherwise
        """
        if not ML_AVAILABLE:
            logger.warning("Cannot train: scikit-learn not available")
            return False
        
        path = Path(log_path)
        if not path.exists():
            logger.warning(f"Log file not found: {log_path}")
            return False
        
        texts = []
        labels = []
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        query = entry.get("query", "")
                        intent = entry.get("intent", "general")
                        
                        if query and intent:
                            texts.append(query)
                            labels.append(intent)
                    except json.JSONDecodeError:
                        continue
            
            if len(texts) < 5:
                logger.warning(f"Not enough training data: {len(texts)} samples")
                return False
            
            # Build pipeline
            self.classifier = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=1000,
                    ngram_range=(1, 2),
                    stop_words='english'
                )),
                ('clf', LogisticRegression(
                    max_iter=1000,
                    random_state=42
                ))
            ])
            
            self.classifier.fit(texts, labels)
            self.trained = True
            
            logger.info(f"Trained intent classifier on {len(texts)} samples")
            return True
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False
    
    def classify_intent(self, query: str) -> Tuple[str, float]:
        """
        Classify intent of a query.
        
        Returns:
            (intent, confidence) tuple
        """
        # Try ML classification first
        if ML_AVAILABLE and self.trained and self.classifier:
            try:
                prediction = self.classifier.predict([query])[0]
                probabilities = self.classifier.predict_proba([query])[0]
                confidence = max(probabilities)
                return prediction, confidence
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
        
        # Fallback to rule-based
        return self._classify_rule_based(query)
    
    def _classify_rule_based(self, query: str) -> Tuple[str, float]:
        """Rule-based intent classification fallback."""
        query_lower = query.lower()
        
        best_intent = "general"
        best_score = 0
        
        for intent, patterns in self.fallback_patterns.items():
            score = sum(1 for pattern in patterns if re.search(pattern, query_lower))
            if score > best_score:
                best_score = score
                best_intent = intent
        
        # Normalize confidence
        confidence = min(best_score / 3.0, 1.0)  # Max 3 pattern matches
        
        return best_intent, confidence


# ── SAFETY GUARD ──────────────────────────────────────────────────────────────
class SafetyGuard:
    """
    SafetyGuard - Content Safety Filtering
    
    Prevents generation of harmful or dangerous code.
    """
    
    DANGEROUS_PATTERNS = [
        r"os\.system\s*\(",
        r"subprocess\..*shell\s*=\s*True",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
        r"open\s*\([^)]*['\"]\/",  # Absolute path access
        r"shutil\.rmtree",
        r"rm\s+-rf",
    ]
    
    def __init__(self):
        self.compiled_patterns = [re.compile(p) for p in self.DANGEROUS_PATTERNS]
        logger.info("SafetyGuard initialized")
    
    def check_code(self, code: str) -> Tuple[bool, str]:
        """
        Check code for dangerous patterns.
        
        Returns:
            (is_safe, reason) tuple
        """
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(code):
                return False, f"Dangerous pattern detected: {self.DANGEROUS_PATTERNS[i]}"
        
        return True, "Code appears safe"
    
    def sanitize_output(self, text: str) -> str:
        """Remove potentially harmful content from output."""
        # Remove any shell commands
        text = re.sub(r'\$\([^)]+\)', '[REMOVED]', text)
        text = re.sub(r'`[^`]+`', '[REMOVED]', text)
        
        return text


# ── EFFECTOR REGISTRY ─────────────────────────────────────────────────────────
class EffectorRegistry:
    """
    EffectorRegistry - Action Registration and Execution
    
    Registers available actions and their handlers.
    """
    
    def __init__(self):
        self.effectors: Dict[str, callable] = {}
        self.metadata: Dict[str, Dict] = {}
        logger.info("EffectorRegistry initialized")
    
    def register(self, name: str, handler: callable, 
                 description: str = "", params: Dict = None):
        """Register an effector (action handler)."""
        self.effectors[name] = handler
        self.metadata[name] = {
            "description": description,
            "params": params or {}
        }
        logger.debug(f"Registered effector: {name}")
    
    def execute(self, name: str, **kwargs) -> Any:
        """Execute a registered effector."""
        if name not in self.effectors:
            raise ValueError(f"Unknown effector: {name}")
        
        handler = self.effectors[name]
        return handler(**kwargs)
    
    def list_effectors(self) -> List[str]:
        """List all registered effectors."""
        return list(self.effectors.keys())
    
    def get_metadata(self, name: str) -> Dict:
        """Get metadata for an effector."""
        return self.metadata.get(name, {})


# ── ETHER CONSCIOUSNESS (Main Coordinator) ────────────────────────────────────
class EtherConsciousness:
    """
    EtherConsciousness - Main Coordinator for Neural Architecture
    
    Integrates Hippocampus, Cortex, SafetyGuard, and EffectorRegistry
    into a unified consciousness system.
    """
    
    def __init__(self, project_root: str = None):
        self.hippocampus = Hippocampus()
        self.cortex = Cortex()
        self.safety = SafetyGuard()
        self.registry = EffectorRegistry()
        self.project_root = Path(project_root) if project_root else Path.cwd()
        
        logger.info("EtherConsciousness initialized")
    
    def process_query(self, query: str) -> Dict:
        """Process a query through the consciousness pipeline."""
        # Classify intent
        intent, confidence = self.cortex.classify_intent(query)
        
        # Check safety
        is_safe, reason = self.safety.check_code(query)
        if not is_safe:
            return {
                "type": "error",
                "text": f"Query blocked for safety: {reason}"
            }
        
        # Check prefetch
        prefetch = self.hippocampus.check_prefetch(query)
        
        return {
            "intent": intent,
            "confidence": confidence,
            "prefetch": prefetch,
            "safe": is_safe
        }


# ── SINGLETON ACCESS ──────────────────────────────────────────────────────────
_consciousness_instance: Optional[EtherConsciousness] = None


def get_consciousness(project_root: str = None) -> EtherConsciousness:
    """Get or create EtherConsciousness singleton instance."""
    global _consciousness_instance
    if _consciousness_instance is None:
        _consciousness_instance = EtherConsciousness(project_root)
    return _consciousness_instance
