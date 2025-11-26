"""Cairo/StarkNet Advanced Vulnerability Detector.

This module provides specialized vulnerability detection for Cairo
smart contracts on StarkNet.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List


class CairoVulnType(Enum):
    """Types of Cairo-specific vulnerabilities."""

    FELT_OVERFLOW = "felt_overflow"
    STORAGE_COLLISION = "storage_collision"
    L1_L2_MESSAGING = "l1_l2_messaging"
    PROOF_VERIFICATION = "proof_verification"
    ACCESS_CONTROL = "access_control"
    REENTRANCY = "reentrancy"
    ARRAY_BOUNDS = "array_bounds"
    ASSERT_HANDLING = "assert_handling"
    SIGNATURE_VALIDATION = "signature_validation"
    DELEGATE_CALL = "delegate_call"


class VulnSeverity(Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CairoVulnPattern:
    """A Cairo vulnerability pattern."""

    name: str
    vuln_type: CairoVulnType
    severity: VulnSeverity
    description: str
    patterns: List[str]
    anti_patterns: List[str]
    mitigation: str
    cairo_version: str  # "0.x", "1.x", or "both"


@dataclass
class CairoFinding:
    """A Cairo vulnerability finding."""

    vuln_type: CairoVulnType
    severity: VulnSeverity
    title: str
    description: str
    line_number: int
    code_snippet: str
    confidence: float
    mitigation: str
    cairo_version: str


class CairoAdvancedDetector:
    """Detect Cairo/StarkNet specific vulnerabilities.

    Detects vulnerabilities specific to Cairo smart contracts:
    - Felt overflow
    - Storage collision
    - L1-L2 messaging issues
    - Proof verification flaws
    - Access control issues
    - Reentrancy patterns
    - Array bounds issues
    - Assert handling
    - Signature validation
    - Delegate call issues
    """

    VULNERABILITY_PATTERNS: List[CairoVulnPattern] = [
        CairoVulnPattern(
            name="Felt Overflow",
            vuln_type=CairoVulnType.FELT_OVERFLOW,
            severity=VulnSeverity.HIGH,
            description="Arithmetic operation may overflow felt252 range",
            patterns=[
                r"\+\s*\d+",
                r"\*\s*\d+",
                r"felt252\s*\+",
                r"u256\s*\*",
            ],
            anti_patterns=[
                r"checked_",
                r"safe_",
                r"assert\s*\(",
                r"if\s+\w+\s*>\s*\w+",
            ],
            mitigation="Use checked arithmetic or add explicit overflow checks",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="Storage Collision",
            vuln_type=CairoVulnType.STORAGE_COLLISION,
            severity=VulnSeverity.CRITICAL,
            description="Storage slots may collide causing data corruption",
            patterns=[
                r"@storage_var",
                r"storage::\w+::write",
                r"LegacyMap\s*<",
            ],
            anti_patterns=[
                r"sn_keccak",
                r"pedersen",
                r"unique_storage",
            ],
            mitigation="Use unique storage keys and proper namespacing",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="L1-L2 Messaging Issues",
            vuln_type=CairoVulnType.L1_L2_MESSAGING,
            severity=VulnSeverity.CRITICAL,
            description="L1-L2 message handling vulnerabilities",
            patterns=[
                r"send_message_to_l1",
                r"l1_handler",
                r"@l1_handler",
            ],
            anti_patterns=[
                r"verify_message",
                r"consume_message",
                r"nonce",
            ],
            mitigation="Verify message authenticity and prevent replay attacks",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="Proof Verification Flaws",
            vuln_type=CairoVulnType.PROOF_VERIFICATION,
            severity=VulnSeverity.CRITICAL,
            description="Cryptographic proof verification issues",
            patterns=[
                r"verify_proof",
                r"pedersen\s*\(",
                r"check_signature",
            ],
            anti_patterns=[
                r"assert_valid",
                r"verify_and_",
                r"revert\s*\(",
            ],
            mitigation="Ensure all proof components are validated before acceptance",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="Missing Access Control",
            vuln_type=CairoVulnType.ACCESS_CONTROL,
            severity=VulnSeverity.HIGH,
            description="Functions lack proper access control",
            patterns=[
                r"#\[external\][^#]*fn\s+\w+",
                r"@external[^@]*func\s+\w+",
            ],
            anti_patterns=[
                r"get_caller_address",
                r"assert_only_",
                r"ownable",
                r"access_control",
            ],
            mitigation="Add access control checks using get_caller_address()",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="Reentrancy Vulnerability",
            vuln_type=CairoVulnType.REENTRANCY,
            severity=VulnSeverity.HIGH,
            description="External calls before state updates",
            patterns=[
                r"call_contract\s*\(",
                r"IERC20\w*Dispatcher",
                r"\.transfer\s*\(",
            ],
            anti_patterns=[
                r"reentrancy_guard",
                r"_lock",
                r"entered\s*=\s*true",
            ],
            mitigation="Use reentrancy guards or update state before external calls",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="Array Bounds Issues",
            vuln_type=CairoVulnType.ARRAY_BOUNDS,
            severity=VulnSeverity.MEDIUM,
            description="Array access without bounds checking",
            patterns=[
                r"\.at\s*\(\s*\w+\s*\)",
                r"\[\s*\w+\s*\]",
                r"array_len",
            ],
            anti_patterns=[
                r"if\s+\w+\s*<\s*len",
                r"assert\s*\([^)]*<\s*len",
                r"get\s*\(",
            ],
            mitigation="Use .get() method or check bounds before access",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="Assert Handling Issues",
            vuln_type=CairoVulnType.ASSERT_HANDLING,
            severity=VulnSeverity.MEDIUM,
            description="Improper use of assert statements",
            patterns=[
                r"assert\s*\(\s*\d+\s*==",
                r"assert\s*\(\s*true",
            ],
            anti_patterns=[
                r"assert_with_felt252",
                r"panic_with_felt252",
            ],
            mitigation="Use meaningful assert conditions with proper error messages",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="Signature Validation Issues",
            vuln_type=CairoVulnType.SIGNATURE_VALIDATION,
            severity=VulnSeverity.CRITICAL,
            description="Signature verification vulnerabilities",
            patterns=[
                r"verify_signature",
                r"check_ecdsa_signature",
                r"is_valid_signature",
            ],
            anti_patterns=[
                r"hash_struct",
                r"typed_data",
                r"EIP712",
            ],
            mitigation="Use typed data hashing and verify all signature components",
            cairo_version="both",
        ),
        CairoVulnPattern(
            name="Delegate Call Issues",
            vuln_type=CairoVulnType.DELEGATE_CALL,
            severity=VulnSeverity.CRITICAL,
            description="Unsafe library/delegate call usage",
            patterns=[
                r"library_call",
                r"replace_class_syscall",
                r"library_call_syscall",
            ],
            anti_patterns=[
                r"validate_class_hash",
                r"upgrade_guard",
                r"access_control",
            ],
            mitigation="Validate class hashes and restrict upgrade capabilities",
            cairo_version="both",
        ),
    ]

    def __init__(self, cairo_version: str = "both") -> None:
        """Initialize the Cairo detector.

        Args:
            cairo_version: Target Cairo version ("0.x", "1.x", or "both")
        """
        self.cairo_version = cairo_version
        self.findings: List[CairoFinding] = []

    def detect(self, code: str, file_path: str = "") -> List[CairoFinding]:
        """Detect Cairo-specific vulnerabilities.

        Args:
            code: Cairo source code
            file_path: Optional file path

        Returns:
            List of findings
        """
        self.findings = []
        lines = code.split("\n")

        # Detect Cairo version
        detected_version = self._detect_version(code)

        for pattern in self.VULNERABILITY_PATTERNS:
            # Check version compatibility
            if self.cairo_version != "both" and pattern.cairo_version != "both":
                if self.cairo_version != pattern.cairo_version:
                    continue

            findings = self._detect_pattern(code, lines, pattern, detected_version)
            self.findings.extend(findings)

        return self.findings

    def _detect_version(self, code: str) -> str:
        """Detect Cairo version from code."""
        # Cairo 1.x indicators
        cairo1_indicators = [
            "mod ",
            "#[contract]",
            "#[starknet::contract]",
            "fn ",
            "->",
            "impl ",
        ]

        # Cairo 0.x indicators
        cairo0_indicators = [
            "%lang starknet",
            "@external",
            "@view",
            "func ",
            "end",
            "local ",
        ]

        cairo1_score = sum(1 for ind in cairo1_indicators if ind in code)
        cairo0_score = sum(1 for ind in cairo0_indicators if ind in code)

        if cairo1_score > cairo0_score:
            return "1.x"
        elif cairo0_score > cairo1_score:
            return "0.x"
        return "both"

    def _detect_pattern(self, code: str, lines: List[str], pattern: CairoVulnPattern, version: str) -> List[CairoFinding]:
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

                    finding = CairoFinding(
                        vuln_type=pattern.vuln_type,
                        severity=pattern.severity,
                        title=pattern.name,
                        description=pattern.description,
                        line_number=line_num,
                        code_snippet=snippet,
                        confidence=confidence,
                        mitigation=pattern.mitigation,
                        cairo_version=version,
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
        by_version = {}

        for f in self.findings:
            sev = f.severity.value
            vtype = f.vuln_type.value
            ver = f.cairo_version

            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_type[vtype] = by_type.get(vtype, 0) + 1
            by_version[ver] = by_version.get(ver, 0) + 1

        return {"total": len(self.findings), "by_severity": by_severity, "by_type": by_type, "by_version": by_version}

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
                "cairo_version": f.cairo_version,
            }
            for f in self.findings
        ]
