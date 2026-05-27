"""
Backward-compatibility shim for core/agent_factory.py.

The canonical implementation has moved to agents/factory.py.
All imports from this module continue to work unchanged.
"""

from agents.factory import AgentFactory  # noqa: F401

__all__ = ["AgentFactory"]
