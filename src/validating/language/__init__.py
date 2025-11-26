"""Multi-language support for smart contract security analysis.

This module provides language-specific vulnerability detection for
Solidity, Rust (Solana), Move (Aptos/Sui), and Cairo (StarkNet).
"""

from .language_detection import LanguageDetector
from .solana_detector import SolanaAdvancedDetector
from .move_detector import MoveAdvancedDetector
from .cairo_detector import CairoAdvancedDetector


__all__ = [
    "LanguageDetector",
    "SolanaAdvancedDetector",
    "MoveAdvancedDetector",
    "CairoAdvancedDetector",
]
