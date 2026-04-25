"""
Ether Composer Module - BACKWARD COMPATIBILITY STUB
====================================================

This module exists solely for backward compatibility.
The benchmark identified the 916-line Composer as overengineered.
Per v5 refactoring recommendations, this is now a minimal stub.

Actual personality/tone should be handled via simple prompt templates,
not a complex stochastic dice engine.
"""

# Minimal stub classes to prevent import errors
class Measure:
    """Stub measure class"""
    def __init__(self, text="", measure_type=None):
        self.text = text
        self.measure_type = measure_type

class MeasureType:
    """Stub measure types"""
    GREETING = "greeting"
    ANALYSIS = "analysis"
    EXPLANATION = "explanation"
    CLOSING = "closing"

class Score:
    """Stub score class"""
    def __init__(self, measures=None):
        self.measures = measures or []

class MeasureLibrary:
    """Stub measure library - no more 176 interchangeable measures"""
    def __init__(self):
        self.measures = {}
    
    def get(self, key):
        return self.measures.get(key, [])

class Conductor:
    """Stub conductor - simplified from 916 lines to essential interface"""
    def __init__(self):
        self.library = MeasureLibrary()
    
    def compose(self, query, intent):
        """Return empty composition - let LLM handle personality"""
        return ""

class CompositionalCortex:
    """Stub compositional cortex"""
    def __init__(self):
        self.conductor = Conductor()
    
    def generate_response(self, query, context=None):
        """Return None - caller should use standard LLM response"""
        return None

# Global instance
_composer = None

def get_composer():
    """Return stub composer instance"""
    global _composer
    if _composer is None:
        _composer = Conductor()
    return _composer

def get_compositional_cortex():
    """Return stub compositional cortex instance"""
    return CompositionalCortex()
