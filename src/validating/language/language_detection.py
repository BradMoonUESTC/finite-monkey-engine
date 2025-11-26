"""Language Detection for Multi-Chain Smart Contract Analysis.

This module provides detection of blockchain programming languages
and routing to appropriate language-specific analyzers.
"""

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple


class BlockchainLanguage(Enum):
    """Supported blockchain programming languages."""

    SOLIDITY = "solidity"
    RUST = "rust"  # Solana, Near, Polkadot
    MOVE = "move"  # Aptos, Sui
    CAIRO = "cairo"  # StarkNet
    VYPER = "vyper"  # Ethereum
    UNKNOWN = "unknown"


class BlockchainPlatform(Enum):
    """Blockchain platforms."""

    ETHEREUM = "ethereum"  # Solidity/Vyper
    SOLANA = "solana"  # Rust + Anchor
    NEAR = "near"  # Rust
    POLKADOT = "polkadot"  # Rust + ink!
    APTOS = "aptos"  # Move
    SUI = "sui"  # Move
    STARKNET = "starknet"  # Cairo
    MONAD = "monad"  # Solidity (EVM-compatible with parallel execution)
    POLYGON = "polygon"  # Solidity
    ARBITRUM = "arbitrum"  # Solidity
    OPTIMISM = "optimism"  # Solidity
    BSC = "bsc"  # Solidity
    AVALANCHE = "avalanche"  # Solidity
    BASE = "base"  # Solidity
    UNKNOWN = "unknown"


@dataclass
class LanguageInfo:
    """Information about detected language."""

    language: BlockchainLanguage
    platform: BlockchainPlatform
    confidence: float  # 0.0 to 1.0
    file_extension: str
    framework: Optional[str] = None  # e.g., "anchor", "ink", "hardhat"
    version: Optional[str] = None


@dataclass
class FileAnalysis:
    """Analysis result for a single file."""

    file_path: str
    language_info: LanguageInfo
    line_count: int
    has_tests: bool
    has_dependencies: bool


class LanguageDetector:
    """Detect blockchain programming languages and platforms.

    Supported languages:
    - Solidity (.sol) - Ethereum, Monad, Polygon, BSC, Arbitrum, etc.
    - Rust (.rs) - Solana, Near, Polkadot
    - Move (.move) - Aptos, Sui
    - Cairo (.cairo) - StarkNet
    - Vyper (.vy) - Ethereum
    """

    # File extension mappings
    EXTENSION_MAP = {
        ".sol": BlockchainLanguage.SOLIDITY,
        ".vy": BlockchainLanguage.VYPER,
        ".rs": BlockchainLanguage.RUST,
        ".move": BlockchainLanguage.MOVE,
        ".cairo": BlockchainLanguage.CAIRO,
    }

    # Language-specific patterns
    LANGUAGE_PATTERNS = {
        BlockchainLanguage.SOLIDITY: [
            r"pragma\s+solidity",
            r"contract\s+\w+\s*(is\s+\w+)?",
            r"function\s+\w+\s*\([^)]*\)\s*(public|private|internal|external)",
            r"import\s+[\"']@openzeppelin",
        ],
        BlockchainLanguage.VYPER: [
            r"@external",
            r"@internal",
            r"@view",
            r"@pure",
            r"from\s+vyper",
        ],
        BlockchainLanguage.RUST: [
            r"use\s+anchor_lang",
            r"use\s+solana_program",
            r"#\[program\]",
            r"#\[derive\(Accounts\)\]",
            r"pub\s+fn\s+\w+",
            r"impl\s+\w+\s+for",
        ],
        BlockchainLanguage.MOVE: [
            r"module\s+\w+::\w+",
            r"struct\s+\w+\s+has",
            r"public\s+entry\s+fun",
            r"use\s+\w+::\w+",
            r"#\[resource\]",
        ],
        BlockchainLanguage.CAIRO: [
            r"@contract_interface",
            r"@external",
            r"@view",
            r"func\s+\w+\{",
            r"from\s+starkware",
            r"%lang\s+starknet",
        ],
    }

    # Platform-specific patterns
    PLATFORM_PATTERNS = {
        BlockchainPlatform.SOLANA: [
            r"use\s+anchor_lang",
            r"use\s+solana_program",
            r"#\[program\]",
            r"Pubkey",
            r"AccountInfo",
        ],
        BlockchainPlatform.NEAR: [
            r"use\s+near_sdk",
            r"#\[near_bindgen\]",
            r"Promise::",
        ],
        BlockchainPlatform.POLKADOT: [
            r"use\s+ink_lang",
            r"#\[ink::contract\]",
            r"ink_storage",
        ],
        BlockchainPlatform.APTOS: [
            r"aptos_framework",
            r"aptos_std",
            r"signer::address_of",
        ],
        BlockchainPlatform.SUI: [
            r"use\s+sui::",
            r"sui::transfer",
            r"sui::object",
            r"TxContext",
        ],
        BlockchainPlatform.STARKNET: [
            r"starkware",
            r"%lang\s+starknet",
            r"@storage_var",
        ],
    }

    # Framework patterns
    FRAMEWORK_PATTERNS = {
        "hardhat": [r"import\s+[\"']hardhat", r"hardhat\.config"],
        "foundry": [r"forge-std", r"import\s+[\"']forge-std"],
        "truffle": [r"truffle-config", r"artifacts\.require"],
        "anchor": [r"anchor_lang", r"#\[program\]"],
        "ink": [r"ink_lang", r"#\[ink::contract\]"],
    }

    def __init__(self) -> None:
        """Initialize the language detector."""
        self.detected_files: List[FileAnalysis] = []

    def detect_from_file(self, file_path: str, content: Optional[str] = None) -> LanguageInfo:
        """Detect language from a file.

        Args:
            file_path: Path to the file
            content: Optional file content (reads file if not provided)

        Returns:
            Language information
        """
        # Get extension
        ext = os.path.splitext(file_path)[1].lower()

        # Initial guess from extension
        language = self.EXTENSION_MAP.get(ext, BlockchainLanguage.UNKNOWN)

        # Read content if not provided
        if content is None:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
            except (FileNotFoundError, OSError):
                return LanguageInfo(language=language, platform=BlockchainPlatform.UNKNOWN, confidence=0.3, file_extension=ext)

        # Verify language from content
        language, lang_confidence = self._detect_language_from_content(content, language)

        # Detect platform
        platform, platform_confidence = self._detect_platform(content, language)

        # Detect framework
        framework = self._detect_framework(content)

        # Detect version
        version = self._detect_version(content, language)

        # Calculate overall confidence
        confidence = (lang_confidence + platform_confidence) / 2

        return LanguageInfo(
            language=language, platform=platform, confidence=confidence, file_extension=ext, framework=framework, version=version
        )

    def detect_from_content(self, content: str, file_extension: str = "") -> LanguageInfo:
        """Detect language from content string.

        Args:
            content: File content
            file_extension: Optional file extension hint

        Returns:
            Language information
        """
        # Try extension hint
        initial_language = self.EXTENSION_MAP.get(file_extension.lower(), BlockchainLanguage.UNKNOWN)

        # Detect from content
        language, lang_confidence = self._detect_language_from_content(content, initial_language)
        platform, platform_confidence = self._detect_platform(content, language)
        framework = self._detect_framework(content)
        version = self._detect_version(content, language)

        confidence = (lang_confidence + platform_confidence) / 2

        return LanguageInfo(
            language=language, platform=platform, confidence=confidence, file_extension=file_extension, framework=framework, version=version
        )

    def detect_from_directory(self, directory: str) -> Dict[BlockchainLanguage, int]:
        """Detect languages in a directory.

        Args:
            directory: Path to directory

        Returns:
            Dictionary mapping languages to file counts
        """
        language_counts: Dict[BlockchainLanguage, int] = {}
        self.detected_files = []

        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                if ext in self.EXTENSION_MAP:
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()

                        lang_info = self.detect_from_content(content, ext)
                        language_counts[lang_info.language] = language_counts.get(lang_info.language, 0) + 1

                        analysis = FileAnalysis(
                            file_path=file_path,
                            language_info=lang_info,
                            line_count=content.count("\n") + 1,
                            has_tests="test" in file_path.lower(),
                            has_dependencies=self._has_dependencies(content, lang_info.language),
                        )
                        self.detected_files.append(analysis)
                    except (FileNotFoundError, OSError):
                        continue

        return language_counts

    def _detect_language_from_content(
        self, content: str, hint: BlockchainLanguage = BlockchainLanguage.UNKNOWN
    ) -> Tuple[BlockchainLanguage, float]:
        """Detect language from content.

        Args:
            content: File content
            hint: Optional language hint

        Returns:
            Tuple of (language, confidence)
        """
        scores: Dict[BlockchainLanguage, int] = {}

        for language, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    score += 1
            scores[language] = score

        # Find highest score
        if scores:
            best_lang = max(scores, key=lambda x: scores[x])
            max_score = scores[best_lang]
            max_possible = len(self.LANGUAGE_PATTERNS.get(best_lang, []))

            if max_score > 0:
                confidence = min(1.0, (max_score / max_possible) + 0.3)
                return best_lang, confidence

        # Fall back to hint
        if hint != BlockchainLanguage.UNKNOWN:
            return hint, 0.5

        return BlockchainLanguage.UNKNOWN, 0.0

    def _detect_platform(self, content: str, language: BlockchainLanguage) -> Tuple[BlockchainPlatform, float]:
        """Detect blockchain platform from content.

        Args:
            content: File content
            language: Detected language

        Returns:
            Tuple of (platform, confidence)
        """
        # Map languages to default platforms
        default_platforms = {
            BlockchainLanguage.SOLIDITY: BlockchainPlatform.ETHEREUM,
            BlockchainLanguage.VYPER: BlockchainPlatform.ETHEREUM,
            BlockchainLanguage.RUST: BlockchainPlatform.SOLANA,  # Most common
            BlockchainLanguage.MOVE: BlockchainPlatform.APTOS,  # Will check for Sui
            BlockchainLanguage.CAIRO: BlockchainPlatform.STARKNET,
        }

        # Check platform-specific patterns
        for platform, patterns in self.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return platform, 0.8

        # Return default for language
        default = default_platforms.get(language, BlockchainPlatform.UNKNOWN)
        return default, 0.6 if default != BlockchainPlatform.UNKNOWN else 0.0

    def _detect_framework(self, content: str) -> Optional[str]:
        """Detect development framework from content.

        Args:
            content: File content

        Returns:
            Framework name or None
        """
        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return framework
        return None

    def _detect_version(self, content: str, language: BlockchainLanguage) -> Optional[str]:
        """Detect language version from content.

        Args:
            content: File content
            language: Detected language

        Returns:
            Version string or None
        """
        version_patterns = {
            BlockchainLanguage.SOLIDITY: r"pragma\s+solidity\s*[\^~>=<]*([0-9]+\.[0-9]+\.[0-9]+)",
            BlockchainLanguage.VYPER: r"#\s*@version\s+([0-9]+\.[0-9]+)",
            BlockchainLanguage.CAIRO: r"%lang\s+starknet\s*([0-9]+)?",
        }

        pattern = version_patterns.get(language)
        if pattern:
            match = re.search(pattern, content)
            if match:
                return match.group(1)

        return None

    def _has_dependencies(self, content: str, language: BlockchainLanguage) -> bool:
        """Check if file has external dependencies.

        Args:
            content: File content
            language: Detected language

        Returns:
            True if has dependencies
        """
        dep_patterns = {
            BlockchainLanguage.SOLIDITY: r"import\s+[\"']",
            BlockchainLanguage.RUST: r"use\s+\w+::",
            BlockchainLanguage.MOVE: r"use\s+\w+::",
            BlockchainLanguage.CAIRO: r"from\s+\w+",
        }

        pattern = dep_patterns.get(language)
        if pattern:
            return bool(re.search(pattern, content))

        return False

    def get_appropriate_detector(self, language_info: LanguageInfo):
        """Get the appropriate vulnerability detector for a language.

        Args:
            language_info: Detected language information

        Returns:
            Appropriate detector instance
        """
        from .solana_detector import SolanaAdvancedDetector
        from .move_detector import MoveAdvancedDetector
        from .cairo_detector import CairoAdvancedDetector
        from validating.detectors import EconomicExploitDetector

        if language_info.language == BlockchainLanguage.RUST:
            if language_info.platform == BlockchainPlatform.SOLANA:
                return SolanaAdvancedDetector()

        if language_info.language == BlockchainLanguage.MOVE:
            return MoveAdvancedDetector()

        if language_info.language == BlockchainLanguage.CAIRO:
            return CairoAdvancedDetector()

        # Default to Solidity detector
        return EconomicExploitDetector()

    def get_summary(self) -> Dict:
        """Get summary of detected files.

        Returns:
            Summary dictionary
        """
        if not self.detected_files:
            return {"files": 0}

        language_counts: Dict[str, int] = {}
        platform_counts: Dict[str, int] = {}
        framework_counts: Dict[str, int] = {}

        total_lines = 0
        test_files = 0

        for analysis in self.detected_files:
            lang = analysis.language_info.language.value
            platform = analysis.language_info.platform.value
            framework = analysis.language_info.framework or "none"

            language_counts[lang] = language_counts.get(lang, 0) + 1
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            framework_counts[framework] = framework_counts.get(framework, 0) + 1

            total_lines += analysis.line_count
            if analysis.has_tests:
                test_files += 1

        return {
            "files": len(self.detected_files),
            "languages": language_counts,
            "platforms": platform_counts,
            "frameworks": framework_counts,
            "total_lines": total_lines,
            "test_files": test_files,
        }
