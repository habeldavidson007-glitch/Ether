"""
Ether Core Module - The Consciousness Engine
=============================================
This module contains the unified consciousness engine that coordinates
all Ether subsystems into a single autonomous agent.
"""

from .consciousness import (
    EtherConsciousness,
    Hippocampus,
    Cortex,
    EffectorRegistry,
    ConsciousState,
    ThoughtProcess,
    create_consciousness
)

__all__ = [
    "EtherConsciousness",
    "Hippocampus",
    "Cortex",
    "EffectorRegistry",
    "ConsciousState",
    "ThoughtProcess",
    "create_consciousness"
]
