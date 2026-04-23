"""
Ether Cortex Engine - Consolidated Brain
=========================================
This module contains the unified Cortex engine that combines
intent classification, decision making, and query orchestration.

This is the new consolidated brain of Ether, merging previous
Builder and Consciousness functionality into a single optimized engine.
"""

# Import everything from consciousness.py for backward compatibility
# This is the NEW primary location for the Cortex class
from .consciousness import (
    Cortex,
    EtherConsciousness,
    Hippocampus,
    EffectorRegistry,
    SafetyGuard,
    detect_ram_and_suggest_model,
    GODOT_KEYWORDS,
    ML_AVAILABLE,
    MemoryUnit,
    get_consciousness
)

__all__ = [
    "Cortex",
    "EtherConsciousness",
    "Hippocampus",
    "EffectorRegistry",
    "SafetyGuard",
    "detect_ram_and_suggest_model",
    "GODOT_KEYWORDS",
    "ML_AVAILABLE",
    "MemoryUnit",
    "get_consciousness"
]
