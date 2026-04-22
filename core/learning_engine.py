"""
Feedback Trainer / Learning Engine
----------------------------------
Implements "Agent Lightning" concept: Trains Ether to be smarter via feedback loops.
Learns from accepted/rejected code fixes to adapt to project-specific patterns.

Key Features:
- Self-Optimization: Learns from user feedback automatically.
- Pattern Recognition: Identifies successful vs failed fix patterns.
- Style Adaptation: Adapts to project coding conventions over time.
- No Fine-tuning: Uses retrieval-augmented learning instead of model weights update.

How It Works:
1. User accepts/rejects a code fix → Feedback recorded.
2. System extracts features from the interaction (file type, error type, fix pattern).
3. Similar future queries retrieve successful past fixes as few-shot examples.
4. LLM generates better responses based on learned patterns.
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class FeedbackEntry:
    """Represents a single feedback interaction."""
    
    def __init__(self, entry_id: str, query: str, original_code: str, 
                 suggested_fix: str, user_feedback: str,  # 'accepted' or 'rejected'
                 file_path: str = "", error_type: str = "", 
                 metadata: Optional[Dict] = None):
        self.entry_id = entry_id
        self.timestamp = datetime.now().isoformat()
        self.query = query
        self.original_code = original_code
        self.suggested_fix = suggested_fix
        self.user_feedback = user_feedback
        self.file_path = file_path
        self.error_type = error_type
        self.metadata = metadata or {}
        
        # Extracted features for pattern matching
        self.features = self._extract_features()
        
    def _extract_features(self) -> Dict[str, Any]:
        """Extract key features for pattern matching."""
        import re
        features = {
            "file_extension": Path(self.file_path).suffix if self.file_path else "unknown",
            "error_type": self.error_type or "general",
            "query_length": len(self.query),
            "code_lines": len(self.original_code.split('\n')),
            "fix_lines": len(self.suggested_fix.split('\n')),
            "has_function": "func " in self.original_code or "def " in self.original_code,
            "has_class": "class " in self.original_code,
            "keywords": self._extract_keywords()
        }
        return features
        
    def _extract_keywords(self) -> List[str]:
        """Extract important keywords from query and code."""
        import re
        text = f"{self.query} {self.original_code}".lower()
        # Common GDScript/programming keywords
        keywords = re.findall(r'\b(?:signal|export|onready|var|const|enum|func|class|extends|yield|await|match|break|continue|return|if|elif|else|for|while|try|catch|except|finally|node|scene|tree|process|physics|input)\b', text)
        return list(set(keywords))
        
    def to_dict(self) -> Dict:
        return {
            "id": self.entry_id,
            "timestamp": self.timestamp,
            "query": self.query[:200],  # Truncate for storage
            "original_code": self.original_code[:500],
            "suggested_fix": self.suggested_fix[:500],
            "file_path": self.file_path,
            "error_type": self.error_type,
            "feedback": self.user_feedback,
            "features": self.features
        }


class LearningEngine:
    """
    Main trainer that learns from feedback and improves future responses.
    
    Implements Agent Lightning concepts:
    - Plugs into any agent workflow (Ether, AutoGen, LangChain, etc.)
    - Continuously improves via feedback loop
    - No model retraining needed (uses RAG-style retrieval of successful patterns)
    """
    
    def __init__(self, storage_path: str = "feedback_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.feedback_file = self.storage_path / "feedback_log.json"
        self.patterns_file = self.storage_path / "learned_patterns.json"
        
        # In-memory cache
        self.feedback_history: List[FeedbackEntry] = []
        self.learned_patterns: Dict[str, List[Dict]] = defaultdict(list)
        
        # Statistics
        self.total_accepted = 0
        self.total_rejected = 0
        self.success_rate = 0.0
        
        self._load_data()
        
    def _load_data(self):
        """Load existing feedback data."""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r') as f:
                    data = json.load(f)
                    self.feedback_history = [
                        FeedbackEntry(
                            entry_id=item['id'],
                            query=item.get('query', ''),
                            original_code=item.get('original_code', ''),
                            suggested_fix=item.get('suggested_fix', ''),
                            user_feedback=item['feedback'],
                            file_path=item.get('file_path', ''),
                            error_type=item.get('error_type', ''),
                            metadata={}
                        )
                        for item in data
                    ]
                self._recalculate_stats()
                print(f"[LearningEngine] Loaded {len(self.feedback_history)} feedback entries")
            except Exception as e:
                print(f"[LearningEngine] Error loading data: {e}")
                
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, 'r') as f:
                    self.learned_patterns = defaultdict(list, json.load(f))
                print(f"[LearningEngine] Loaded {len(self.learned_patterns)} pattern categories")
            except Exception as e:
                print(f"[LearningEngine] Error loading patterns: {e}")
                
    def _save_data(self):
        """Persist feedback data to disk."""
        try:
            with open(self.feedback_file, 'w') as f:
                json.dump([entry.to_dict() for entry in self.feedback_history], f, indent=2)
                
            with open(self.patterns_file, 'w') as f:
                json.dump(dict(self.learned_patterns), f, indent=2)
        except Exception as e:
            print(f"[LearningEngine] Error saving data: {e}")
            
    def _recalculate_stats(self):
        """Recalculate success statistics."""
        self.total_accepted = sum(1 for e in self.feedback_history if e.user_feedback == 'accepted')
        self.total_rejected = sum(1 for e in self.feedback_history if e.user_feedback == 'rejected')
        total = self.total_accepted + self.total_rejected
        self.success_rate = (self.total_accepted / total * 100) if total > 0 else 0.0
        
    def record_feedback(self, query: str, original_code: str, suggested_fix: str,
                       user_feedback: str, file_path: str = "", error_type: str = "",
                       metadata: Optional[Dict] = None) -> str:
        """
        Record user feedback for a code suggestion.
        
        Args:
            query: User's original question/request
            original_code: Code before the fix
            suggested_fix: Code suggested by Ether
            user_feedback: 'accepted' or 'rejected'
            file_path: Path to the file being modified
            error_type: Type of error being fixed (if any)
            metadata: Additional context
            
        Returns:
            Entry ID for tracking
        """
        entry_id = hashlib.md5(f"{datetime.now().isoformat()}:{query[:50]}".encode()).hexdigest()[:12]
        
        entry = FeedbackEntry(
            entry_id=entry_id,
            query=query,
            original_code=original_code,
            suggested_fix=suggested_fix,
            user_feedback=user_feedback,
            file_path=file_path,
            error_type=error_type,
            metadata=metadata
        )
        
        self.feedback_history.append(entry)
        self._recalculate_stats()
        
        # Update learned patterns
        self._update_patterns(entry)
        
        # Save to disk
        self._save_data()
        
        print(f"[LearningEngine] Recorded {user_feedback} feedback (Success Rate: {self.success_rate:.1f}%)")
        return entry_id
        
    def _update_patterns(self, entry: FeedbackEntry):
        """Update learned patterns based on new feedback."""
        # Only learn from accepted fixes
        if entry.user_feedback != 'accepted':
            return
            
        # Categorize by error type and file extension
        category = f"{entry.features['error_type']}_{entry.features['file_extension']}"
        
        pattern = {
            "query_pattern": entry.query[:100],
            "keywords": entry.features['keywords'],
            "fix_preview": entry.suggested_fix[:200],
            "success_count": 1,
            "last_used": entry.timestamp
        }
        
        # Check if similar pattern exists
        existing = self.learned_patterns[category]
        similar_found = False
        
        for p in existing:
            # Simple similarity check: shared keywords
            shared_keywords = set(p['keywords']) & set(pattern['keywords'])
            if len(shared_keywords) >= 2:
                p['success_count'] += 1
                p['last_used'] = pattern['last_used']
                similar_found = True
                break
                
        if not similar_found:
            self.learned_patterns[category].append(pattern)
            
        # Keep only top 20 patterns per category
        self.learned_patterns[category] = sorted(
            self.learned_patterns[category],
            key=lambda x: x['success_count'],
            reverse=True
        )[:20]
        
    def get_learning_context(self, query: str, file_path: str = "", 
                            error_type: str = "") -> List[Dict]:
        """
        Retrieve relevant learned patterns for current query.
        Use this to inject few-shot examples into LLM prompts.
        
        Args:
            query: Current user query
            file_path: File being worked on
            error_type: Type of error (if known)
            
        Returns:
            List of successful past fixes as context examples
        """
        # Determine category
        ext = Path(file_path).suffix if file_path else ".gd"
        category = f"{error_type}_{ext}" if error_type else f"general_{ext}"
        
        candidates = []
        
        # Get patterns from specific category
        if category in self.learned_patterns:
            candidates.extend(self.learned_patterns[category])
            
        # Also get from general category
        if f"general_{ext}" in self.learned_patterns:
            candidates.extend(self.learned_patterns[f"general_{ext}"])
            
        # Find similar queries in feedback history
        query_keywords = set(query.lower().split())
        for entry in self.feedback_history[-100:]:  # Recent history
            if entry.user_feedback == 'accepted':
                entry_keywords = set(entry.query.lower().split())
                similarity = len(query_keywords & entry_keywords) / max(len(query_keywords), 1)
                if similarity > 0.3:
                    candidates.append({
                        "query_example": entry.query,
                        "fix_example": entry.suggested_fix[:300],
                        "relevance": similarity
                    })
                    
        # Sort by relevance/success count
        candidates = sorted(
            candidates,
            key=lambda x: x.get('success_count', 0) + x.get('relevance', 0) * 10,
            reverse=True
        )
        
        return candidates[:5]  # Top 5 examples
        
    def generate_training_prompt(self, query: str, file_path: str = "", 
                                error_type: str = "") -> str:
        """
        Generate a prompt section with learned examples for the LLM.
        
        Returns:
            Formatted string with few-shot examples
        """
        examples = self.get_learning_context(query, file_path, error_type)
        
        if not examples:
            return ""
            
        prompt_section = "\n\n## Learned Patterns from Previous Successes:\n"
        prompt_section += "Based on previously accepted fixes in this project, consider these patterns:\n\n"
        
        for i, ex in enumerate(examples, 1):
            if 'fix_example' in ex:
                prompt_section += f"Example {i}:\n"
                prompt_section += f"  Query: \"{ex.get('query_example', 'N/A')[:100]}...\"\n"
                prompt_section += f"  Successful Fix Approach: {ex.get('fix_example', 'N/A')[:150]}...\n\n"
            elif 'fix_preview' in ex:
                prompt_section += f"Pattern {i} ({ex.get('success_count', 1)} successes):\n"
                prompt_section += f"  Keywords: {', '.join(ex.get('keywords', [])[:5])}\n"
                prompt_section += f"  Approach: {ex.get('fix_preview', 'N/A')[:150]}...\n\n"
                
        prompt_section += "Apply similar reasoning and style to the current task.\n"
        return prompt_section
        
    def get_stats(self) -> Dict:
        """Get training statistics."""
        return {
            "total_feedback": len(self.feedback_history),
            "accepted": self.total_accepted,
            "rejected": self.total_rejected,
            "success_rate": f"{self.success_rate:.1f}%",
            "pattern_categories": len(self.learned_patterns),
            "total_patterns": sum(len(p) for p in self.learned_patterns.values())
        }
        
    def export_report(self, output_path: str):
        """Export a detailed learning report."""
        report = {
            "summary": self.get_stats(),
            "top_patterns": {},
            "recent_feedback": [e.to_dict() for e in self.feedback_history[-20:]]
        }
        
        # Include top 3 patterns per category
        for category, patterns in self.learned_patterns.items():
            report["top_patterns"][category] = patterns[:3]
            
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"[LearningEngine] Report exported to {output_path}")


# Singleton instance
_instance: Optional[LearningEngine] = None

def get_learning_engine(storage_path: str = "feedback_data") -> LearningEngine:
    """Get or create the singleton LearningEngine instance."""
    global _instance
    if _instance is None:
        _instance = LearningEngine(storage_path)
    return _instance


if __name__ == "__main__":
    # Test the LearningEngine
    print("=== Testing LearningEngine ===\n")
    
    engine = get_learning_engine("test_feedback")
    
    # Record some test feedback
    entry_id = engine.record_feedback(
        query="Fix null reference in player script",
        original_code="func _ready():\n    player.health = 100",
        suggested_fix="func _ready():\n    if player:\n        player.health = 100",
        user_feedback="accepted",
        file_path="player.gd",
        error_type="null_reference"
    )
    print(f"Recorded feedback entry: {entry_id}")
    
    # Record another
    engine.record_feedback(
        query="Optimize loop in enemy AI",
        original_code="for enemy in enemies:\n    if enemy.distance < 10:\n        attack()",
        suggested_fix="var nearby_enemies = enemies.filter(func(e): return e.distance < 10)\nfor enemy in nearby_enemies:\n    attack()",
        user_feedback="accepted",
        file_path="enemy_ai.gd",
        error_type="performance"
    )
    
    # Record a rejection
    engine.record_feedback(
        query="Add error handling",
        original_code="var data = load_file(path)",
        suggested_fix="var data = load_file(path) if File.file_exists(path) else null",
        user_feedback="rejected",
        file_path="utils.gd",
        error_type="error_handling"
    )
    
    # Get stats
    print("\n=== Statistics ===")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Get learning context
    print("\n=== Learning Context for 'fix null player' ===")
    context = engine.get_learning_context("fix null player reference", "player.gd", "null_reference")
    for i, ex in enumerate(context):
        print(f"\nExample {i+1}:")
        print(f"  {ex}")
    
    # Generate training prompt
    print("\n=== Training Prompt ===")
    prompt = engine.generate_training_prompt("optimize enemy loop", "enemy_ai.gd", "performance")
    print(prompt)
    
    print("\n✅ LearningEngine test complete!")
