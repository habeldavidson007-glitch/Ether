"""
Ether Personality Module
========================

Compositional AI personality engine for social interactions, greetings, 
and creative conversations.

This module contains the Composer Engine moved from core/ to separate
personality concerns from practical task execution.

Usage:
- Greetings and casual conversations
- Creative/opinion questions  
- Complex explanations needing personality
- Social interactions (~20% of queries)

For practical tasks (coding, documents, math, etc.), use core/writer.py
"""

from .composer import (
    Conductor,
    MeasureLibrary, 
    CompositionalCortex,
    get_composer,
    get_compositional_cortex,
    Measure,
    MeasureType,
    Score
)

__all__ = [
    'Conductor',
    'MeasureLibrary',
    'CompositionalCortex', 
    'get_composer',
    'get_compositional_cortex',
    'Measure',
    'MeasureType',
    'Score'
]
