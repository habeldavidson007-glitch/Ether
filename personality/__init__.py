"""
Ether Personality Module - Simplified
======================================

Lightweight personality configuration for social interactions.
Replaces the 900-line composer.py with a simple ToneConfig dataclass.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ToneConfig:
    """Simple tone configuration for responses."""
    system_prefix: str = ""
    style: str = "helpful"  # helpful, friendly, professional, concise
    temperature: float = 0.7
    
    def get_system_message(self) -> str:
        """Get the system message prefix for this tone."""
        prefixes = {
            'helpful': "You are a helpful AI assistant.",
            'friendly': "You are a friendly and approachable AI assistant.",
            'professional': "You are a professional AI assistant.",
            'concise': "You are a concise AI assistant. Be brief and direct."
        }
        base = prefixes.get(self.style, prefixes['helpful'])
        if self.system_prefix:
            return f"{self.system_prefix} {base}"
        return base


# Default configurations
DEFAULT_TONE = ToneConfig()
FRIENDLY_TONE = ToneConfig(style='friendly')
PROFESSIONAL_TONE = ToneConfig(style='professional')
CONCISE_TONE = ToneConfig(style='concise', temperature=0.5)


def get_composer():
    """Return default tone config (backward compatibility)."""
    return DEFAULT_TONE


def get_compositional_cortex():
    """Return default tone config (backward compatibility)."""
    return DEFAULT_TONE


# Backward compatibility stubs
Conductor = ToneConfig
MeasureLibrary = ToneConfig  
CompositionalCortex = ToneConfig
Measure = ToneConfig
MeasureType = str
Score = float

__all__ = [
    'ToneConfig',
    'get_composer',
    'get_compositional_cortex',
    'DEFAULT_TONE',
    'FRIENDLY_TONE', 
    'PROFESSIONAL_TONE',
    'CONCISE_TONE',
    'Conductor',
    'MeasureLibrary',
    'CompositionalCortex',
    'Measure',
    'MeasureType',
    'Score'
]
