"""
ether/core/ml_intent.py
========================
ML-Based Intent Classification for Ether AI Assistant

This module provides intent classification using scikit-learn with a
fallback to rule-based matching when ML is unavailable or fails.

Features:
- Lazy loading of scikit-learn to minimize memory usage
- Automatic training from conversation logs
- Graceful fallback to keyword-based rules
- Never crashes - always returns a valid intent

Usage:
    from ether.core.ml_intent import MLIntentClassifier
    
    classifier = MLIntentClassifier()
    intent = classifier.predict("How do I fix this bug?")
    print(intent)  # Output: "debug"
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)


class MLIntentClassifier:
    """
    Intent classifier using TF-IDF + Logistic Regression with rule-based fallback.
    
    Intents supported:
    - 'debug': Fix bugs, errors, issues
    - 'explain': Understand concepts, how things work
    - 'create': Generate new code, files, features
    - 'optimize': Improve performance, refactor
    - 'search': Find information, documentation
    - 'general': General questions, chat
    """
    
    # Fallback keyword mappings (used when ML is unavailable)
    KEYWORD_INTENTS = {
        'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
        'debug': ['fix', 'bug', 'error', 'crash', 'issue', 'problem', 'broken', 
                  'wrong', 'fail', 'exception', 'traceback', 'debug'],
        'explain': ['explain', 'understand', 'what', 'how', 'why', 'concept', 
                    'theory', 'meaning', 'describe', 'tell me about'],
        'create': ['create', 'make', 'generate', 'write', 'build', 'new', 
                   'implement', 'add', 'code', 'function', 'class'],
        'optimize': ['optimize', 'improve', 'faster', 'performance', 'refactor', 
                     'efficient', 'speed', 'memory', 'better'],
        'search': ['find', 'search', 'look', 'locate', 'where', 'documentation', 
                   'reference', 'example', 'tutorial'],
    }
    
    DEFAULT_INTENT = 'general'
    
    def __init__(self):
        """Initialize the classifier with lazy sklearn loading."""
        self._vectorizer = None
        self._model = None
        self._is_trained = False
        self._sklearn_available = False
        self._classes: List[str] = []
        
        # Try to load sklearn lazily
        self._try_load_sklearn()
        
        logger.info(f"MLIntentClassifier initialized (sklearn available: {self._sklearn_available})")
    
    def _try_load_sklearn(self) -> bool:
        """Attempt to load scikit-learn components."""
        if self._sklearn_available:
            return True
            
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            
            self._TfidfVectorizer = TfidfVectorizer
            self._LogisticRegression = LogisticRegression
            self._sklearn_available = True
            logger.debug("scikit-learn loaded successfully")
            return True
        except ImportError as e:
            logger.warning(f"scikit-learn not available: {e}. Using rule-based fallback.")
            self._sklearn_available = False
            return False
    
    def train_from_logs(self, log_path: Optional[str] = None) -> bool:
        """
        Train the model from conversation logs.
        
        Args:
            log_path: Path to conversations.jsonl file. If None, uses default location.
            
        Returns:
            True if training succeeded, False otherwise.
        """
        if not self._sklearn_available:
            logger.warning("Cannot train: scikit-learn not available")
            return False
        
        # Default log path
        if log_path is None:
            project_root = Path(__file__).parent.parent.parent
            log_path = project_root / "logs" / "conversations.jsonl"
        
        log_path = Path(log_path)
        
        if not log_path.exists():
            logger.warning(f"No conversation logs found at {log_path}")
            return False
        
        # Load training data
        queries = []
        intents = []
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        query = entry.get('query', '') or entry.get('user_input', '') or entry.get('input', '')
                        intent = entry.get('intent', '') or entry.get('classification', '')
                        
                        if query and intent:
                            queries.append(query)
                            intents.append(intent)
                    except json.JSONDecodeError:
                        continue
            
            if len(queries) < 5:
                logger.warning(f"Not enough training samples ({len(queries)}). Need at least 5.")
                return False
            
            # Train the model
            self._vectorizer = self._TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 2),
                stop_words='english',
                lowercase=True
            )
            
            X = self._vectorizer.fit_transform(queries)
            
            self._model = self._LogisticRegression(
                max_iter=500,
                random_state=42,
                n_jobs=1  # Single thread for low memory
            )
            
            self._model.fit(X, intents)
            self._classes = list(self._model.classes_)
            self._is_trained = True
            
            logger.info(f"Trained on {len(queries)} samples. Classes: {self._classes}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to train from logs: {e}", exc_info=True)
            return False
    
    def predict(self, query: str) -> str:
        """
        Predict the intent of a query.
        
        Args:
            query: The user's input text
            
        Returns:
            The predicted intent string (e.g., 'debug', 'explain', 'create')
        """
        if not query or not isinstance(query, str):
            return self.DEFAULT_INTENT
        
        query = query.strip()
        
        if not query:
            return self.DEFAULT_INTENT
        
        # Try ML prediction first
        if self._sklearn_available and self._is_trained and self._model is not None:
            try:
                X = self._vectorizer.transform([query])
                prediction = self._model.predict(X)[0]
                confidence = max(self._model.predict_proba(X)[0])
                
                logger.debug(f"ML prediction: {prediction} (confidence: {confidence:.2f})")
                
                # Only use ML prediction if confidence is reasonable
                if confidence > 0.3:
                    return prediction
                else:
                    logger.debug(f"Low confidence ({confidence:.2f}), falling back to rules")
                    
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}. Using fallback.")
        
        # Fallback to rule-based keyword matching
        return self._rule_based_predict(query)
    
    def _rule_based_predict(self, query: str) -> str:
        """
        Rule-based intent prediction using keyword matching.
        
        This is the fallback when ML is unavailable or fails.
        """
        query_lower = query.lower()
        
        best_intent = self.DEFAULT_INTENT
        best_score = 0
        
        for intent, keywords in self.KEYWORD_INTENTS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            
            if score > best_score:
                best_score = score
                best_intent = intent
        
        # If no meaningful keywords matched (score too low), return general
        # Exception: greetings only need 1 match since they're common short phrases
        if best_score < 2 and best_intent != 'greeting':
            return self.DEFAULT_INTENT
        
        logger.debug(f"Rule-based prediction: {best_intent} (score: {best_score})")
        return best_intent
    
    def predict_with_confidence(self, query: str) -> Tuple[str, float]:
        """
        Predict intent with confidence score.
        
        Returns:
            Tuple of (intent, confidence) where confidence is 0.0-1.0
        """
        if self._sklearn_available and self._is_trained and self._model is not None:
            try:
                X = self._vectorizer.transform([query])
                probs = self._model.predict_proba(X)[0]
                prediction = self._model.predict(X)[0]
                confidence = float(max(probs))
                return prediction, confidence
            except Exception:
                pass
        
        # Fallback - estimate confidence based on keyword matches
        intent = self._rule_based_predict(query)
        query_lower = query.lower()
        
        if intent == self.DEFAULT_INTENT:
            return intent, 0.1
        
        keywords = self.KEYWORD_INTENTS.get(intent, [])
        match_count = sum(1 for kw in keywords if kw in query_lower)
        confidence = min(0.7, match_count * 0.2)  # Cap at 0.7 for rule-based
        
        return intent, confidence
    
    @property
    def is_ml_available(self) -> bool:
        """Check if ML capabilities are available."""
        return self._sklearn_available and self._is_trained
    
    @property
    def available_intents(self) -> List[str]:
        """Get list of available intent classes."""
        if self._is_trained and self._classes:
            return self._classes
        return list(self.KEYWORD_INTENTS.keys()) + [self.DEFAULT_INTENT]


# Unified keyword mappings from all deprecated classifiers
GODOT_KEYWORDS = {
    'debug': ['fix', 'bug', 'error', 'crash', 'issue', 'problem', 'broken', 
              'wrong', 'fail', 'exception', 'traceback', 'debug', 'null', 'nil'],
    'explain': ['explain', 'understand', 'what', 'how', 'why', 'concept', 
                'theory', 'meaning', 'describe', 'tell me about', 'difference between'],
    'create': ['create', 'make', 'generate', 'write', 'build', 'new', 
               'implement', 'add', 'code', 'function', 'class', 'script', 'node'],
    'optimize': ['optimize', 'improve', 'faster', 'performance', 'refactor', 
                 'efficient', 'speed', 'memory', 'better', 'lag', 'slow'],
    'search': ['find', 'search', 'look', 'locate', 'where', 'documentation', 
               'reference', 'example', 'tutorial', 'show me'],
    'chat': ['hello', 'hi', 'hey', 'thanks', 'thank you', 'goodbye', 'bye']
}


# Convenience function for quick intent detection - UNIFIED ENTRY POINT
def classify_intent(query: str) -> str:
    """
    Quick intent classification without managing classifier instance.
    
    This is the SINGLE unified entry point for all intent classification.
    Replaces: detect_intent_fast(), classify(), Cortex.classify_intent(), 
              QueryRouter.route(), route_query() in all daemons.
    
    Args:
        query: User input text
        
    Returns:
        Predicted intent string ('debug', 'explain', 'create', 'optimize', 'search', 'chat', 'general')
    """
    classifier = MLIntentClassifier()
    return classifier.predict(query)


def detect_intent_fast(query: str) -> str:
    """
    Fast path intent detection using optimized keyword matching.
    Deprecated: Use classify_intent() instead. This is kept for backward compatibility.
    """
    return classify_intent(query)


def classify(text: str) -> str:
    """
    Legacy classify function from context_manager.py.
    Deprecated: Use classify_intent() instead. This is kept for backward compatibility.
    """
    return classify_intent(text)


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    classifier = MLIntentClassifier()
    
    test_queries = [
        "How do I fix this error?",
        "Explain how GDScript works",
        "Create a new player controller",
        "Optimize this loop for better performance",
        "Where can I find documentation?",
        "Hello, how are you?"
    ]
    
    print("\nIntent Classification Test")
    print("=" * 50)
    
    for query in test_queries:
        intent = classifier.predict(query)
        print(f"Query: {query}")
        print(f"Intent: {intent}")
        print("-" * 50)
