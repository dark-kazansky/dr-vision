"""
Backward-compatibility shim for core/background_tasks.py.

The canonical implementation has moved to services/job_manager.py.
All imports from this module continue to work unchanged.
"""

from services.job_manager import JobManager, job_manager  # noqa: F401

__all__ = ["JobManager", "job_manager"]
