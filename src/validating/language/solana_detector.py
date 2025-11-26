"""Solana/Rust Advanced Vulnerability Detector.

This module provides specialized vulnerability detection for Solana
smart contracts written in Rust, with focus on Anchor framework patterns.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional


class SolanaVulnType(Enum):
    """Types of Solana-specific vulnerabilities."""

    MISSING_SIGNER_CHECK = "missing_signer_check"
    MISSING_OWNER_CHECK = "missing_owner_check"
    ACCOUNT_CONFUSION = "account_confusion"
    ARBITRARY_CPI = "arbitrary_cpi"
    INTEGER_OVERFLOW = "integer_overflow"
    MISSING_DISCRIMINATOR = "missing_discriminator"
    PDA_DERIVATION = "pda_derivation"
    FLASH_LOAN = "flash_loan"
    RENT_EXEMPTION = "rent_exemption"
    CLOSE_ACCOUNT = "close_account"
    DUPLICATE_MUTABLE = "duplicate_mutable"
    TYPE_COSPLAY = "type_cosplay"


class VulnSeverity(Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SolanaVulnPattern:
    """A Solana vulnerability pattern."""

    name: str
    vuln_type: SolanaVulnType
    severity: VulnSeverity
    description: str
    patterns: List[str]
    anti_patterns: List[str]  # Patterns that indicate the vuln is mitigated
    mitigation: str
    references: List[str]


@dataclass
class SolanaFinding:
    """A Solana vulnerability finding."""

    vuln_type: SolanaVulnType
    severity: VulnSeverity
    title: str
    description: str
    line_number: int
    code_snippet: str
    confidence: float
    mitigation: str
    references: List[str]


class SolanaAdvancedDetector:
    """Detect Solana/Rust-specific vulnerabilities.

    Detects vulnerabilities specific to Solana smart contracts:
    - Missing signer checks
    - Missing owner checks
    - Account confusion/type confusion
    - Arbitrary CPI (Cross-Program Invocation)
    - Integer overflow without checked_ methods
    - Missing discriminator checks
    - PDA derivation issues
    - Flash loan attacks (Solend, Mango)
    - Rent exemption issues
    - Account closing vulnerabilities
    - Duplicate mutable accounts
    - Type cosplay attacks
    """

    VULNERABILITY_PATTERNS: List[SolanaVulnPattern] = [
        SolanaVulnPattern(
            name="Missing Signer Check",
            vuln_type=SolanaVulnType.MISSING_SIGNER_CHECK,
            severity=VulnSeverity.CRITICAL,
            description="Function modifies state without verifying the signer",
            patterns=[
                r"pub\s+fn\s+\w+\s*<[^>]*>\s*\([^)]*\)\s*->\s*\w+\s*\{(?:(?!is_signer|Signer<)[\s\S])*\}",
                r"accounts\.\w+\.key\s*==\s*[^;]+(?!\.is_signer)",
            ],
            anti_patterns=[
                r"Signer<'info>",
                r"\.is_signer",
                r"require!\s*\([^)]*is_signer",
            ],
            mitigation="Use Anchor's Signer<'info> type or manually check is_signer property",
            references=[
                "https://github.com/coral-xyz/sealevel-attacks/blob/master/programs/0-signer-authorization/",
            ],
        ),
        SolanaVulnPattern(
            name="Missing Owner Check",
            vuln_type=SolanaVulnType.MISSING_OWNER_CHECK,
            severity=VulnSeverity.CRITICAL,
            description="Account ownership not verified before use",
            patterns=[
                r"Account<'info,\s*\w+>(?!.*owner\s*=)",
                r"AccountInfo<'info>(?:(?!\.owner|owner\s*==)[\s\S]){0,100}\.try_borrow",
            ],
            anti_patterns=[
                r"owner\s*=\s*",
                r"\.owner\s*==",
                r"assert_eq!\s*\([^)]*owner",
            ],
            mitigation="Use Anchor's owner constraint or manually verify account.owner",
            references=[
                "https://github.com/coral-xyz/sealevel-attacks/blob/master/programs/1-owner-checks/",
            ],
        ),
        SolanaVulnPattern(
            name="Account Type Confusion",
            vuln_type=SolanaVulnType.ACCOUNT_CONFUSION,
            severity=VulnSeverity.HIGH,
            description="Account can be confused with another account type",
            patterns=[
                r"AccountInfo<'info>.*\.try_borrow_mut_data",
                r"Account<'info,\s*\w+>(?!.*constraint)",
            ],
            anti_patterns=[
                r"discriminator",
                r"has_one\s*=",
                r"constraint\s*=",
                r"#\[account\(.*discriminator",
            ],
            mitigation="Use account discriminators and Anchor constraints",
            references=[
                "https://github.com/coral-xyz/sealevel-attacks/blob/master/programs/3-type-cosplay/",
            ],
        ),
        SolanaVulnPattern(
            name="Arbitrary CPI",
            vuln_type=SolanaVulnType.ARBITRARY_CPI,
            severity=VulnSeverity.CRITICAL,
            description="Cross-program invocation with arbitrary program ID",
            patterns=[
                r"invoke\s*\(\s*&Instruction\s*\{[^}]*program_id:\s*\*?\w+",
                r"invoke_signed\s*\([^)]*\*?\w+\.key",
            ],
            anti_patterns=[
                r"program_id:\s*&(?:spl_token|system_program|anchor_lang)",
                r"PROGRAM_ID",
                r"ID",
                r"id\(\)",
            ],
            mitigation="Hardcode expected program IDs or use Anchor's program attribute",
            references=[
                "https://github.com/coral-xyz/sealevel-attacks/blob/master/programs/4-arbitrary-cpi/",
            ],
        ),
        SolanaVulnPattern(
            name="Integer Overflow Without Checked Math",
            vuln_type=SolanaVulnType.INTEGER_OVERFLOW,
            severity=VulnSeverity.HIGH,
            description="Arithmetic operations without overflow checking",
            patterns=[
                r"\+\s*\d+",  # Simple addition
                r"\*\s*\d+",  # Simple multiplication
                r"amount\s*\+",
                r"balance\s*-",
            ],
            anti_patterns=[
                r"\.checked_add",
                r"\.checked_sub",
                r"\.checked_mul",
                r"\.checked_div",
                r"\.saturating_",
                r"\.overflowing_",
            ],
            mitigation="Use checked_add, checked_sub, checked_mul, checked_div methods",
            references=[
                "https://github.com/coral-xyz/sealevel-attacks/blob/master/programs/5-overflow/",
            ],
        ),
        SolanaVulnPattern(
            name="Missing Discriminator Check",
            vuln_type=SolanaVulnType.MISSING_DISCRIMINATOR,
            severity=VulnSeverity.HIGH,
            description="Account discriminator not verified",
            patterns=[
                r"try_from_slice\s*\(",
                r"deserialize\s*\(",
                r"unpack\s*\(",
            ],
            anti_patterns=[
                r"DISCRIMINATOR",
                r"discriminator",
                r"Account<",  # Anchor handles this
            ],
            mitigation="Use Anchor accounts or manually verify the 8-byte discriminator",
            references=[
                "https://www.anchor-lang.com/docs/account-types",
            ],
        ),
        SolanaVulnPattern(
            name="PDA Derivation Issues",
            vuln_type=SolanaVulnType.PDA_DERIVATION,
            severity=VulnSeverity.HIGH,
            description="Incorrect or missing PDA seed verification",
            patterns=[
                r"find_program_address\s*\(\s*&\s*\[\s*\]",  # Empty seeds
                r"Pubkey::find_program_address(?![\s\S]*bump)",
            ],
            anti_patterns=[
                r"bump\s*=",
                r"seeds\s*=",
                r"find_program_address\s*\(\s*&\s*\[[^\]]+\]",
            ],
            mitigation="Include proper seeds and verify bump seed in PDA derivation",
            references=[
                "https://docs.solana.com/developing/programming-model/calling-between-programs#program-derived-addresses",
            ],
        ),
        SolanaVulnPattern(
            name="Flash Loan Vulnerability",
            vuln_type=SolanaVulnType.FLASH_LOAN,
            severity=VulnSeverity.CRITICAL,
            description="Vulnerable to flash loan attacks",
            patterns=[
                r"flash_loan",
                r"get_reserve\s*\(",
                r"borrow\s*\([^)]*amount",
            ],
            anti_patterns=[
                r"reentrancy",
                r"lock",
                r"flash_loan_fee",
            ],
            mitigation="Implement reentrancy guards and validate state before/after flash loan",
            references=[
                "https://rekt.news/mango-markets-rekt/",
            ],
        ),
        SolanaVulnPattern(
            name="Rent Exemption Issues",
            vuln_type=SolanaVulnType.RENT_EXEMPTION,
            severity=VulnSeverity.MEDIUM,
            description="Account may fall below rent-exempt threshold",
            patterns=[
                r"lamports\s*-=",
                r"\.try_borrow_mut_lamports\s*\(\s*\)\s*\?\s*-=",
            ],
            anti_patterns=[
                r"minimum_balance",
                r"rent_exempt",
                r"Rent::get",
            ],
            mitigation="Always verify account remains rent-exempt after withdrawals",
            references=[
                "https://docs.solana.com/developing/programming-model/accounts#rent-exemption",
            ],
        ),
        SolanaVulnPattern(
            name="Unsafe Account Closing",
            vuln_type=SolanaVulnType.CLOSE_ACCOUNT,
            severity=VulnSeverity.HIGH,
            description="Account closed without proper cleanup",
            patterns=[
                r"\.close\s*\(",
                r"lamports\s*=\s*0",
                r"data\.fill\s*\(\s*0\s*\)",
            ],
            anti_patterns=[
                r"close\s*=\s*\w+",  # Anchor close
                r"\.realloc\s*\(\s*0",
                r"CLOSED_ACCOUNT_DISCRIMINATOR",
            ],
            mitigation="Use Anchor's close constraint or zero out data and lamports properly",
            references=[
                "https://github.com/coral-xyz/sealevel-attacks/blob/master/programs/9-closing-accounts/",
            ],
        ),
        SolanaVulnPattern(
            name="Duplicate Mutable Accounts",
            vuln_type=SolanaVulnType.DUPLICATE_MUTABLE,
            severity=VulnSeverity.HIGH,
            description="Same account passed multiple times as mutable",
            patterns=[
                r"#\[account\(mut\)\][^#]*#\[account\(mut\)\]",
                r"AccountInfo<'info>.*AccountInfo<'info>",
            ],
            anti_patterns=[
                r"constraint\s*=.*!=",
                r"has_one",
            ],
            mitigation="Add constraints to ensure accounts are unique",
            references=[
                "https://github.com/coral-xyz/sealevel-attacks/blob/master/programs/8-duplicate-mutable-accounts/",
            ],
        ),
        SolanaVulnPattern(
            name="Type Cosplay Attack",
            vuln_type=SolanaVulnType.TYPE_COSPLAY,
            severity=VulnSeverity.HIGH,
            description="Account can impersonate another account type",
            patterns=[
                r"AccountInfo<'info>\s*,(?:(?!discriminator)[\s\S]){0,200}\.data",
            ],
            anti_patterns=[
                r"discriminator",
                r"Account<'info",
                r"#\[account\]",
            ],
            mitigation="Use typed accounts with discriminators",
            references=[
                "https://github.com/coral-xyz/sealevel-attacks/blob/master/programs/3-type-cosplay/",
            ],
        ),
    ]

    def __init__(self) -> None:
        """Initialize the Solana detector."""
        self.findings: List[SolanaFinding] = []

    def detect(self, code: str, file_path: str = "") -> List[SolanaFinding]:
        """Detect Solana-specific vulnerabilities.

        Args:
            code: Rust source code
            file_path: Optional file path

        Returns:
            List of findings
        """
        self.findings = []
        lines = code.split("\n")

        for pattern in self.VULNERABILITY_PATTERNS:
            findings = self._detect_pattern(code, lines, pattern)
            self.findings.extend(findings)

        return self.findings

    def _detect_pattern(self, code: str, lines: List[str], pattern: SolanaVulnPattern) -> List[SolanaFinding]:
        """Detect a specific vulnerability pattern."""
        findings = []

        for regex in pattern.patterns:
            try:
                for match in re.finditer(regex, code, re.MULTILINE | re.IGNORECASE):
                    line_num = code[: match.start()].count("\n") + 1
                    start_line = max(0, line_num - 2)
                    end_line = min(len(lines), line_num + 2)
                    snippet = "\n".join(lines[start_line:end_line])

                    # Check for anti-patterns (mitigations)
                    context_start = max(0, match.start() - 300)
                    context_end = min(len(code), match.end() + 300)
                    context = code[context_start:context_end]

                    is_mitigated = any(re.search(ap, context, re.IGNORECASE) for ap in pattern.anti_patterns)

                    if is_mitigated:
                        continue

                    # Calculate confidence
                    confidence = 0.7 if len(pattern.patterns) > 1 else 0.6

                    finding = SolanaFinding(
                        vuln_type=pattern.vuln_type,
                        severity=pattern.severity,
                        title=pattern.name,
                        description=pattern.description,
                        line_number=line_num,
                        code_snippet=snippet,
                        confidence=confidence,
                        mitigation=pattern.mitigation,
                        references=pattern.references,
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

        for f in self.findings:
            sev = f.severity.value
            vtype = f.vuln_type.value

            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_type[vtype] = by_type.get(vtype, 0) + 1

        return {"total": len(self.findings), "by_severity": by_severity, "by_type": by_type}

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
            }
            for f in self.findings
        ]
