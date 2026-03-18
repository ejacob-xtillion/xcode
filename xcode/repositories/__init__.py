"""
Repository layer for xCode.

Abstracts data access and external system integration.
"""
from xcode.repositories.agent_repository import LaFactoriaRepository
from xcode.repositories.cache_repository import InMemoryCacheRepository
from xcode.repositories.file_repository import LocalFileRepository
from xcode.repositories.graph_repository import XGraphRepository
from xcode.repositories.verification_repository import SubprocessVerificationRepository

__all__ = [
    "LaFactoriaRepository",
    "XGraphRepository",
    "InMemoryCacheRepository",
    "LocalFileRepository",
    "SubprocessVerificationRepository",
]
