"""
Test setup: ensure msbe/shared/src and msbe/services/orchestrator are importable.

The shared library lives in editable form at msbe/shared/src and is
expected to be installed via `pip install -e msbe/shared`. For local
test runs without an editable install we extend sys.path here so the
tests stay self-contained.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SHARED_SRC = os.path.join(ROOT, "shared", "src")
ORCHESTRATOR = os.path.join(ROOT, "services", "orchestrator")

for path in (SHARED_SRC, ORCHESTRATOR):
    if path not in sys.path:
        sys.path.insert(0, path)
