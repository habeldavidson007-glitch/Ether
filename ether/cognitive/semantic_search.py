"""
Semantic Search Engine for Ether AI
Replaces keyword matching with vector-based semantic similarity.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import re


class SemanticSearchEngine:
    """
    Lightweight semantic search engine using TF-IDF and cosine similarity.
    Provides better intent understanding than keyword matching.
    """

    def __init__(self):
        self.documents: Dict[str, str] = {}
        self.doc_vectors: Dict[str, Dict[str, float]] = {}
        self.idf_scores: Dict[str, float] = {}
        self.vocab: set = set()
        self._document_count = 0

    def add_document(self, doc_id: str, text: str):
        """Add a document to the search index."""
        self.documents[doc_id] = text
        tokens = self._tokenize(text)
        
        # Update vocabulary
        self.vocab.update(tokens)
        
        # Calculate TF for this document
        tf = defaultdict(int)
        for token in tokens:
            tf[token] += 1
        
        # Normalize TF
        max_freq = max(tf.values()) if tf else 1
        tf_normalized = {k: v / max_freq for k, v in tf.items()}
        
        # Store document vector
        self.doc_vectors[doc_id] = dict(tf_normalized)
        
        # Update IDF scores
        self._document_count += 1
        for token in set(tokens):
            if token not in self.idf_scores:
                self.idf_scores[token] = 1
            else:
                self.idf_scores[token] += 1

    def remove_document(self, doc_id: str):
        """Remove a document from the search index."""
        if doc_id in self.documents:
            del self.documents[doc_id]
            if doc_id in self.doc_vectors:
                del self.doc_vectors[doc_id]
            self._document_count = max(0, self._document_count - 1)

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.1
    ) -> List[Tuple[str, float, str]]:
        """
        Search for documents semantically similar to the query.
        
        Returns list of (doc_id, similarity_score, content) tuples.
        """
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            return []
        
        # Calculate query vector with IDF weighting
        query_vector = self._calculate_query_vector(query_tokens)
        
        if not query_vector:
            return []
        
        # Calculate cosine similarity with all documents
        scores = []
        for doc_id, doc_vector in self.doc_vectors.items():
            similarity = self._cosine_similarity(query_vector, doc_vector)
            if similarity >= threshold:
                scores.append((doc_id, similarity, self.documents.get(doc_id, "")))
        
        # Sort by similarity score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into normalized terms."""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep code-related symbols
        text = re.sub(r'[^\w\s\.\_\-\[\]]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Filter very short tokens and stopwords
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'as', 'into', 'through', 'during', 'before', 'after', 'above',
                     'below', 'between', 'under', 'again', 'further', 'then', 'once'}
        
        return [t for t in tokens if len(t) > 2 and t not in stopwords]

    def _calculate_query_vector(self, tokens: List[str]) -> Dict[str, float]:
        """Calculate query vector with TF-IDF weighting."""
        if not tokens:
            return {}
        
        # Calculate TF
        tf = defaultdict(int)
        for token in tokens:
            tf[token] += 1
        
        max_freq = max(tf.values()) if tf else 1
        tf_normalized = {k: v / max_freq for k, v in tf.items()}
        
        # Apply IDF weighting
        vector = {}
        for token, tf_score in tf_normalized.items():
            if token in self.idf_scores:
                idf = math.log(self._document_count / self.idf_scores[token])
                vector[token] = tf_score * idf
        
        return vector

    def _cosine_similarity(
        self,
        vec1: Dict[str, float],
        vec2: Dict[str, float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        # Find common terms
        common_terms = set(vec1.keys()) & set(vec2.keys())
        
        if not common_terms:
            return 0.0
        
        # Calculate dot product
        dot_product = sum(vec1[term] * vec2[term] for term in common_terms)
        
        # Calculate magnitudes
        mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)

    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "document_count": len(self.documents),
            "vocabulary_size": len(self.vocab),
            "total_tokens": sum(len(self._tokenize(doc)) for doc in self.documents.values())
        }

    def clear(self):
        """Clear the entire index."""
        self.documents.clear()
        self.doc_vectors.clear()
        self.idf_scores.clear()
        self.vocab.clear()
        self._document_count = 0
