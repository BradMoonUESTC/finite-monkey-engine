"""Blockchain utilities for multi-chain support.

This module provides utilities for interacting with multiple blockchains,
including chain configuration and contract fetching.
"""

from .chain_config import ChainConfig
from .chain_config import SUPPORTED_CHAINS
from .contract_fetcher import ContractFetcher


__all__ = [
    "ChainConfig",
    "SUPPORTED_CHAINS",
    "ContractFetcher",
]
