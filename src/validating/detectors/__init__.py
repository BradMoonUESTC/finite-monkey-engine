"""Security detectors for smart contract vulnerability analysis.

This module provides specialized detectors for various types of vulnerabilities
including economic exploits, flash loan attacks, and language-specific issues.
"""

from .economic_exploits import EconomicExploitDetector
from .flash_loan_detector import FlashLoanOracleDetector


__all__ = [
    "EconomicExploitDetector",
    "FlashLoanOracleDetector",
]
