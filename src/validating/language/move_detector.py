"""Move (Aptos/Sui) Advanced Vulnerability Detector.

This module provides specialized vulnerability detection for Move
smart contracts on Aptos and Sui blockchains.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List


class MoveVulnType(Enum):
    """Types of Move-specific vulnerabilities."""

    RESOURCE_HANDLING = "resource_handling"
    CAPABILITY_LEAK = "capability_leak"
    MODULE_ACCESS_CONTROL = "module_access_control"
    GENERIC_TYPE_CONFUSION = "generic_type_confusion"
    SIGNER_CAPABILITY = "signer_capability"
    OBJECT_OWNERSHIP = "object_ownership"
    REENTRANCY = "reentrancy"
    ARITHMETIC = "arithmetic"
    ABORT_HANDLING = "abort_handling"
    PHANTOM_TYPE = "phantom_type"


class VulnSeverity(Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class MoveVulnPattern:
    """A Move vulnerability pattern."""

    name: str
    vuln_type: MoveVulnType
    severity: VulnSeverity
    description: str
    patterns: List[str]
    anti_patterns: List[str]
    mitigation: str
    applies_to: List[str]  # ["aptos", "sui", "both"]


@dataclass
class MoveFinding:
    """A Move vulnerability finding."""

    vuln_type: MoveVulnType
    severity: VulnSeverity
    title: str
    description: str
    line_number: int
    code_snippet: str
    confidence: float
    mitigation: str
    platform: str  # aptos or sui


class MoveAdvancedDetector:
    """Detect Move (Aptos/Sui) specific vulnerabilities.

    Detects vulnerabilities specific to Move smart contracts:
    - Resource handling issues
    - Capability leaks
    - Module access control
    - Generic type confusion
    - Signer capability issues
    - Object ownership (Sui)
    - Reentrancy through modules
    - Arithmetic issues
    - Abort handling
    - Phantom type issues
    """

    VULNERABILITY_PATTERNS: List[MoveVulnPattern] = [
        MoveVulnPattern(
            name="Resource Handling Issues",
            vuln_type=MoveVulnType.RESOURCE_HANDLING,
            severity=VulnSeverity.CRITICAL,
            description="Resources not properly stored, moved, or destroyed",
            patterns=[
                r"let\s+\w+\s*=\s*borrow_global_mut",
                r"move_from\s*<\s*\w+\s*>\s*\([^)]+\)(?![\s\S]*move_to)",
                r"struct\s+\w+\s+has\s+(?!.*drop)",
            ],
            anti_patterns=[
                r"move_to\s*\(",
                r"destroy\s*\(",
                r"has\s+drop",
            ],
            mitigation="Ensure all resources are properly moved, stored, or destroyed",
            applies_to=["both"],
        ),
        MoveVulnPattern(
            name="Capability Leak",
            vuln_type=MoveVulnType.CAPABILITY_LEAK,
            severity=VulnSeverity.CRITICAL,
            description="Capabilities exposed to unauthorized modules",
            patterns=[
                r"public\s+fun\s+\w+\s*\([^)]*\)\s*:\s*&\w*Capability",
                r"copy\s+\w*[Cc]ap",
                r"acquires\s+\w*Capability(?!.*friend)",
            ],
            anti_patterns=[
                r"friend\s+\w+::\w+",
                r"public\(friend\)",
                r"assert!\s*\([^)]*signer",
            ],
            mitigation="Use friend visibility and restrict capability access",
            applies_to=["aptos"],
        ),
        MoveVulnPattern(
            name="Missing Access Control",
            vuln_type=MoveVulnType.MODULE_ACCESS_CONTROL,
            severity=VulnSeverity.HIGH,
            description="Public functions without proper signer verification",
            patterns=[
                r"public\s+entry\s+fun\s+\w+\s*\([^)]*\)(?:(?!signer|ctx)[\s\S]){0,200}\{",
                r"public\s+fun\s+(?:transfer|mint|burn)\w*\s*\([^)]*\)(?![\s\S]*signer)",
            ],
            anti_patterns=[
                r"signer:\s*&signer",
                r"ctx:\s*&\w*TxContext",
                r"assert!\s*\([^)]*signer::address_of",
            ],
            mitigation="Add signer verification for state-changing functions",
            applies_to=["both"],
        ),
        MoveVulnPattern(
            name="Generic Type Confusion",
            vuln_type=MoveVulnType.GENERIC_TYPE_CONFUSION,
            severity=VulnSeverity.HIGH,
            description="Generic types not properly constrained",
            patterns=[
                r"public\s+fun\s+\w+\s*<\s*T\s*>\s*\(",
                r"borrow_global\s*<\s*T\s*>",
            ],
            anti_patterns=[
                r"<\s*T\s*:\s*\w+",  # Type constraint
                r"T:\s*store",
                r"T:\s*key",
                r"type_name::get\s*<\s*T\s*>",
            ],
            mitigation="Add type constraints (store, key, copy, drop) to generic parameters",
            applies_to=["both"],
        ),
        MoveVulnPattern(
            name="Signer Capability Issues",
            vuln_type=MoveVulnType.SIGNER_CAPABILITY,
            severity=VulnSeverity.CRITICAL,
            description="SignerCapability not properly protected",
            patterns=[
                r"SignerCapability\s*\{",
                r"create_signer\s*\(",
                r"account::create_signer_with_capability",
            ],
            anti_patterns=[
                r"friend\s+\w+",
                r"public\(friend\)",
                r"assert!\s*\([^)]*@\w+",
            ],
            mitigation="Store SignerCapability in protected resources, use friend visibility",
            applies_to=["aptos"],
        ),
        MoveVulnPattern(
            name="Object Ownership Issues (Sui)",
            vuln_type=MoveVulnType.OBJECT_OWNERSHIP,
            severity=VulnSeverity.HIGH,
            description="Sui object ownership not properly verified",
            patterns=[
                r"public\s+entry\s+fun\s+\w+\s*\([^)]*&mut\s+\w+",
                r"transfer::\w+\s*\([^)]*\)",
                r"object::delete",
            ],
            anti_patterns=[
                r"tx_context::sender",
                r"object::owner",
                r"assert!\s*\([^)]*owner",
            ],
            mitigation="Verify object ownership before mutations or transfers",
            applies_to=["sui"],
        ),
        MoveVulnPattern(
            name="Module Reentrancy",
            vuln_type=MoveVulnType.REENTRANCY,
            severity=VulnSeverity.HIGH,
            description="Potential reentrancy through module calls",
            patterns=[
                r"call\s*<\s*\w+\s*>\s*\(",
                r"\w+::\w+\s*\([^)]*\)\s*;[^}]*\w+\s*=",
            ],
            anti_patterns=[
                r"reentrancy_guard",
                r"lock\s*\(",
                r"mutex",
            ],
            mitigation="Update state before external module calls",
            applies_to=["both"],
        ),
        MoveVulnPattern(
            name="Arithmetic Issues",
            vuln_type=MoveVulnType.ARITHMETIC,
            severity=VulnSeverity.MEDIUM,
            description="Potential arithmetic overflow or underflow",
            patterns=[
                r"\+\s*\d+",
                r"-\s*\d+",
                r"\*\s*\d+",
                r"\w+\s*\+\s*\w+",
            ],
            anti_patterns=[
                r"checked_",
                r"safe_",
                r"assert!\s*\([^)]*<=",
                r"assert!\s*\([^)]*>=",
            ],
            mitigation="Use checked arithmetic or add overflow checks",
            applies_to=["both"],
        ),
        MoveVulnPattern(
            name="Improper Abort Handling",
            vuln_type=MoveVulnType.ABORT_HANDLING,
            severity=VulnSeverity.MEDIUM,
            description="Aborts may leave state inconsistent",
            patterns=[
                r"abort\s+\d+",
                r"assert!\s*\(false",
            ],
            anti_patterns=[
                r"transaction_context",
                r"checkpoint",
            ],
            mitigation="Ensure state is consistent before abort points",
            applies_to=["both"],
        ),
        MoveVulnPattern(
            name="Phantom Type Issues",
            vuln_type=MoveVulnType.PHANTOM_TYPE,
            severity=VulnSeverity.MEDIUM,
            description="Phantom type parameters not properly used",
            patterns=[
                r"struct\s+\w+\s*<\s*phantom\s+\w+\s*>",
                r"phantom\s+\w+(?![\s\S]*type_name)",
            ],
            anti_patterns=[
                r"type_name::get",
                r"type_info::",
            ],
            mitigation="Validate phantom types at runtime when security-critical",
            applies_to=["both"],
        ),
    ]

    def __init__(self, platform: str = "both") -> None:
        """Initialize the Move detector.

        Args:
            platform: Target platform ("aptos", "sui", or "both")
        """
        self.platform = platform
        self.findings: List[MoveFinding] = []

    def detect(self, code: str, file_path: str = "") -> List[MoveFinding]:
        """Detect Move-specific vulnerabilities.

        Args:
            code: Move source code
            file_path: Optional file path

        Returns:
            List of findings
        """
        self.findings = []
        lines = code.split("\n")

        # Auto-detect platform if not specified
        detected_platform = self._detect_platform(code)

        for pattern in self.VULNERABILITY_PATTERNS:
            # Check if pattern applies to this platform
            if self.platform != "both" and pattern.applies_to != ["both"]:
                if self.platform not in pattern.applies_to:
                    continue

            findings = self._detect_pattern(code, lines, pattern, detected_platform)
            self.findings.extend(findings)

        return self.findings

    def _detect_platform(self, code: str) -> str:
        """Detect whether code is for Aptos or Sui."""
        sui_indicators = ["sui::", "TxContext", "object::new", "transfer::"]
        aptos_indicators = ["aptos_framework", "aptos_std", "signer::address_of"]

        sui_score = sum(1 for ind in sui_indicators if ind in code)
        aptos_score = sum(1 for ind in aptos_indicators if ind in code)

        if sui_score > aptos_score:
            return "sui"
        elif aptos_score > sui_score:
            return "aptos"
        return "both"

    def _detect_pattern(self, code: str, lines: List[str], pattern: MoveVulnPattern, platform: str) -> List[MoveFinding]:
        """Detect a specific vulnerability pattern."""
        findings = []

        for regex in pattern.patterns:
            try:
                for match in re.finditer(regex, code, re.MULTILINE | re.IGNORECASE):
                    line_num = code[: match.start()].count("\n") + 1
                    start_line = max(0, line_num - 2)
                    end_line = min(len(lines), line_num + 2)
                    snippet = "\n".join(lines[start_line:end_line])

                    # Check for anti-patterns
                    context_start = max(0, match.start() - 300)
                    context_end = min(len(code), match.end() + 300)
                    context = code[context_start:context_end]

                    is_mitigated = any(re.search(ap, context, re.IGNORECASE) for ap in pattern.anti_patterns)

                    if is_mitigated:
                        continue

                    confidence = 0.7

                    finding = MoveFinding(
                        vuln_type=pattern.vuln_type,
                        severity=pattern.severity,
                        title=pattern.name,
                        description=pattern.description,
                        line_number=line_num,
                        code_snippet=snippet,
                        confidence=confidence,
                        mitigation=pattern.mitigation,
                        platform=platform,
                    )
                    findings.append(finding)
            except re.error:
                continue

        return findings

    def get_summary(self) -> Dict:
        """Get detection summary."""
        if not self.findings:
            return {"total": 0}

        by_severity = {}
        by_type = {}
        by_platform = {}

        for f in self.findings:
            sev = f.severity.value
            vtype = f.vuln_type.value
            plat = f.platform

            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_type[vtype] = by_type.get(vtype, 0) + 1
            by_platform[plat] = by_platform.get(plat, 0) + 1

        return {"total": len(self.findings), "by_severity": by_severity, "by_type": by_type, "by_platform": by_platform}

    def to_json(self) -> List[Dict]:
        """Export findings as JSON."""
        return [
            {
                "vuln_type": f.vuln_type.value,
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description,
                "line_number": f.line_number,
                "confidence": f.confidence,
                "mitigation": f.mitigation,
                "platform": f.platform,
            }
            for f in self.findings
        ]
