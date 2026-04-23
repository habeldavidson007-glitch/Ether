"""
Ether Core Module - The Consciousness Engine
=============================================
This module contains the unified consciousness engine that coordinates
all Ether subsystems into a single autonomous agent.

NOTE: cortex.py is now the primary import location for the consolidated brain.
This module maintains backward compatibility by re-exporting from consciousness.py.
"""

# Primary imports from consciousness (the actual implementation)
from .consciousness import (
    Cortex,
    EtherConsciousness,
    Hippocampus,
    EffectorRegistry,
    SafetyGuard,
    get_consciousness,
    detect_ram_and_suggest_model,
    GODOT_KEYWORDS,
    ML_AVAILABLE,
    MemoryUnit,
    COMPRESSION_LEVEL,
    MAX_MEMORY_SIZE_MB
)

__all__ = [
    # Main classes
    "Cortex",
    "EtherConsciousness", 
    "Hippocampus",
    "EffectorRegistry",
    "SafetyGuard",
    "get_consciousness",
    # Utilities
    "detect_ram_and_suggest_model",
    "GODOT_KEYWORDS",
    "ML_AVAILABLE",
    "MemoryUnit",
    "COMPRESSION_LEVEL",
    "MAX_MEMORY_SIZE_MB"
]
