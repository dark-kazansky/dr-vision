"""
Storage package for Doc Intelligence — persistent data layer.

Provides:
    BankingRepository — async PostgreSQL repository for banking data mining results.
    banking_repo      — module-level singleton instance (lazy-initialized).
"""

from storage.banking_repository import BankingRepository

__all__ = ["BankingRepository"]
