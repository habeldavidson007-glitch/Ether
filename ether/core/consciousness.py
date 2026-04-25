"""
Ether Consciousness Module - BACKWARD COMPATIBILITY STUB
=========================================================

This module exists solely for backward compatibility.
All actual implementation has been consolidated into core/cortex.py per v5 refactoring.

The benchmark identified this as overengineered and recommended deletion.
This stub prevents import errors while the codebase transitions.
"""

# Stub constants that were referenced
GODOT_KEYWORDS = ['godot', 'gdscript', 'scene', 'node', 'physics', 'animation']
ML_AVAILABLE = False  # ML features disabled per refactoring
COMPRESSION_LEVEL = 1
MAX_MEMORY_SIZE_MB = 100

# Stub classes for backward compatibility - define locally to avoid circular import
class Cortex:
    """Stub - use Cortex from core.cortex instead"""
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Import Cortex from core.cortex directly, not ether.core.consciousness")

class EtherConsciousness:
    """Stub - use Cortex from core.cortex instead"""
    def __init__(self):
        raise NotImplementedError("Use Cortex from core.cortex instead")

class Hippocampus:
    """Stub - memory functionality consolidated into AdaptiveMemory"""
    def __init__(self, *args, **kwargs):
        pass
    
    def check_prefetch(self, query):
        """Stub prefetch check - returns None (no prefetch available)"""
        return None

class EffectorRegistry:
    """Stub - registry functionality consolidated"""
    def __init__(self):
        self.effects = {}

class SafetyGuard:
    """Stub - safety moved to core.safety"""
    def __init__(self):
        pass
    
    def check(self, content):
        return True

class MemoryUnit:
    """Stub - memory consolidated into adaptive_memory"""
    def __init__(self, *args, **kwargs):
        pass

def get_consciousness():
    """Return None - import Cortex from core.cortex directly"""
    return None

def detect_ram_and_suggest_model():
    """Stub - returns conservative defaults"""
    return {"ram_gb": 4, "suggested_model": "Qwen2.5-1.5B-Instruct"}

def get_cortex():
    """Stub - import from core.cortex directly"""
    return None

class WatchdogMonitor:
    """Stub - use from core.cortex directly"""
    def __init__(self, *args, **kwargs):
        pass
