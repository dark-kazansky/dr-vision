"""
Service URL resolution.

Centralises the env-var lookup for inter-service calls so each service
loads the same defaults and rules.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceURLs:
    """Resolved base URLs for every MSBE service."""

    orchestrator: str
    parser: str
    classifier: str
    extractor: str
    splitter: str
    schema_generator: str

    @classmethod
    def from_env(cls) -> "ServiceURLs":
        return cls(
            orchestrator=os.getenv("ORCHESTRATOR_SERVICE_URL", "http://orchestrator:8091"),
            parser=os.getenv("PARSER_SERVICE_URL", "http://parser:8001"),
            classifier=os.getenv("CLASSIFIER_SERVICE_URL", "http://classifier:8002"),
            extractor=os.getenv("EXTRACTOR_SERVICE_URL", "http://extractor:8003"),
            splitter=os.getenv("SPLITTER_SERVICE_URL", "http://splitter:8004"),
            schema_generator=os.getenv("SCHEMA_GENERATOR_SERVICE_URL", "http://schema-generator:8005"),
        )
