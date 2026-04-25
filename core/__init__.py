"""
Core package for Ether.

This module intentionally avoids eager imports to keep test collection and
lightweight tooling environments stable.
"""


def run_pipeline(*args, **kwargs):
    """Lazy-load Cortex pipeline to avoid heavy import side effects."""
    from .cortex import run_pipeline as _run_pipeline

    return _run_pipeline(*args, **kwargs)


__all__ = ["run_pipeline"]
