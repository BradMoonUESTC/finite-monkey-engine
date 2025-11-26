"""Threat Intelligence Engine for Smart Contract Security.

This module provides real-time threat intelligence integration including
known exploit pattern matching, historical incident analysis, and risk scoring.
"""

import re
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple


class ThreatCategory(Enum):
    """Categories of security threats."""

    REENTRANCY = "reentrancy"
    FLASH_LOAN = "flash_loan"
    ORACLE_MANIPULATION = "oracle_manipulation"
    ACCESS_CONTROL = "access_control"
    INTEGER_OVERFLOW = "integer_overflow"
    SIGNATURE_REPLAY = "signature_replay"
    FRONT_RUNNING = "front_running"
    GOVERNANCE = "governance"
    BRIDGE = "bridge"
    LOGIC_ERROR = "logic_error"
    PRICE_MANIPULATION = "price_manipulation"
    VAULT_EXPLOIT = "vault_exploit"


class ThreatSeverity(Enum):
    """Threat severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ExploitPattern:
    """A known exploit pattern."""

    name: str
    category: ThreatCategory
    description: str
    code_patterns: List[str]
    indicators: List[str]
    severity: ThreatSeverity
    first_seen: str  # Date string
    references: List[str]


@dataclass
class HistoricalIncident:
    """A historical security incident."""

    name: str
    date: str
    protocol: str
    category: ThreatCategory
    loss_amount: float  # In USD
    description: str
    attack_vector: str
    lessons_learned: List[str]
    references: List[str]


@dataclass
class ThreatMatch:
    """A match between code and known threat pattern."""

    pattern: ExploitPattern
    confidence: float  # 0.0 to 1.0
    matched_code: str
    line_number: int
    similar_incidents: List[HistoricalIncident]
    risk_score: int  # 0-100
    recommendations: List[str]


@dataclass
class ThreatAlert:
    """A security alert for monitoring."""

    alert_id: str
    timestamp: datetime
    threat_category: ThreatCategory
    severity: ThreatSeverity
    title: str
    description: str
    affected_code: str
    recommended_action: str


class ThreatIntelligenceEngine:
    """Real-time threat intelligence integration.

    Features:
    - Known exploit pattern database (DAO hack, Parity wallet, flash loan attacks, etc.)
    - Historical incident matching (The DAO $60M, Cream Finance $130M, etc.)
    - Emerging threat identification
    - Risk score calculation
    - Security recommendations generation
    - Monitoring alerts

    Known Exploit Patterns:
    - DAO Reentrancy Attack
    - Parity Wallet Vulnerability
    - Flash Loan Price Manipulation
    - Integer Overflow/Underflow
    - Front-Running/MEV
    - Signature Replay
    - Access Control Vulnerabilities
    - Price Oracle Manipulation
    """

    # Known exploit patterns database
    KNOWN_PATTERNS: List[ExploitPattern] = [
        ExploitPattern(
            name="DAO Reentrancy Attack",
            category=ThreatCategory.REENTRANCY,
            description="Classic reentrancy where external call precedes state update",
            code_patterns=[
                r"\.call\{value:\s*\w+\}\s*\([^)]*\)\s*;[^}]*\w+\s*=",
                r"transfer\s*\([^)]+\)\s*;[^}]*balance\s*-=",
                r"send\s*\([^)]+\)\s*;[^}]*\w+\s*=",
            ],
            indicators=["call", "transfer", "send", "balance", "withdraw"],
            severity=ThreatSeverity.CRITICAL,
            first_seen="2016-06-17",
            references=[
                "https://blog.ethereum.org/2016/06/17/critical-update-re-dao-vulnerability",
            ],
        ),
        ExploitPattern(
            name="Parity Wallet Library Destruction",
            category=ThreatCategory.ACCESS_CONTROL,
            description="Uninitialized wallet library allowing anyone to become owner",
            code_patterns=[
                r"function\s+initWallet\s*\([^)]*\)\s*(?:public|external)(?!\s+initializer)",
                r"selfdestruct\s*\(\s*msg\.sender\s*\)",
            ],
            indicators=["initWallet", "initContract", "selfdestruct", "suicide"],
            severity=ThreatSeverity.CRITICAL,
            first_seen="2017-11-06",
            references=[
                "https://github.com/paritytech/parity-ethereum/issues/6995",
            ],
        ),
        ExploitPattern(
            name="Flash Loan Oracle Manipulation",
            category=ThreatCategory.FLASH_LOAN,
            description="Using flash loans to manipulate DEX spot prices used as oracles",
            code_patterns=[
                r"getReserves\s*\(\s*\)[^}]*(?:price|value|amount)",
                r"slot0\s*\(\s*\)[^}]*sqrtPrice",
                r"flashLoan[^}]*swap[^}]*deposit",
            ],
            indicators=["flashLoan", "getReserves", "slot0", "swap", "borrow"],
            severity=ThreatSeverity.CRITICAL,
            first_seen="2020-02-15",
            references=[
                "https://www.paradigm.xyz/2020/11/so-you-want-to-use-a-price-oracle",
            ],
        ),
        ExploitPattern(
            name="Integer Overflow/Underflow",
            category=ThreatCategory.INTEGER_OVERFLOW,
            description="Arithmetic operations without overflow protection",
            code_patterns=[
                r"balance\s*-\s*\w+[^}]*require\s*\(\s*balance\s*>=",
                r"unchecked\s*\{[^}]*\+[^}]*\}",
                r"assembly\s*\{[^}]*add\s*\(",
            ],
            indicators=["unchecked", "assembly", "add", "sub", "mul", "overflow"],
            severity=ThreatSeverity.HIGH,
            first_seen="2018-04-22",
            references=[
                "https://github.com/ethereum/solidity/issues/796",
            ],
        ),
        ExploitPattern(
            name="Signature Replay Attack",
            category=ThreatCategory.SIGNATURE_REPLAY,
            description="Missing nonce or chain ID in signed messages",
            code_patterns=[
                r"ecrecover\s*\([^)]*\)(?![^;]*nonce)",
                r"ECDSA\.recover[^}]*(?!nonce|chainId)",
            ],
            indicators=["ecrecover", "recover", "signature", "permit"],
            severity=ThreatSeverity.HIGH,
            first_seen="2018-01-01",
            references=[
                "https://eips.ethereum.org/EIPS/eip-712",
            ],
        ),
        ExploitPattern(
            name="Front-Running / MEV Attack",
            category=ThreatCategory.FRONT_RUNNING,
            description="Transaction ordering manipulation for profit",
            code_patterns=[
                r"swap\w*\([^)]*\)\s*;(?![^}]*deadline)",
                r"addLiquidity[^}]*(?!slippage|minAmount)",
            ],
            indicators=["swap", "trade", "order", "pending", "mempool"],
            severity=ThreatSeverity.MEDIUM,
            first_seen="2019-04-01",
            references=[
                "https://arxiv.org/abs/1904.05234",
            ],
        ),
        ExploitPattern(
            name="Missing Access Control",
            category=ThreatCategory.ACCESS_CONTROL,
            description="Critical functions without proper access restrictions",
            code_patterns=[
                r"function\s+(?:set|update|change)\w*\s*\([^)]*\)\s*(?:public|external)(?!\s+only)",
                r"function\s+(?:mint|burn|transfer)\w*\s*\([^)]*\)\s*(?:public|external)(?!\s+only)",
            ],
            indicators=["public", "external", "onlyOwner", "onlyRole", "auth"],
            severity=ThreatSeverity.CRITICAL,
            first_seen="2017-01-01",
            references=[
                "https://swcregistry.io/docs/SWC-105",
            ],
        ),
        ExploitPattern(
            name="Governance Flash Loan Attack",
            category=ThreatCategory.GOVERNANCE,
            description="Flash borrowing governance tokens to pass malicious proposals",
            code_patterns=[
                r"propose\s*\([^}]*flashLoan",
                r"castVote\s*\([^)]*\)(?![^}]*snapshot)",
            ],
            indicators=["propose", "vote", "castVote", "quorum", "flashLoan"],
            severity=ThreatSeverity.HIGH,
            first_seen="2020-10-01",
            references=[
                "https://blog.tally.xyz/governance-and-flash-loans",
            ],
        ),
        ExploitPattern(
            name="Read-Only Reentrancy",
            category=ThreatCategory.REENTRANCY,
            description="Reentrancy through view functions that return stale data",
            code_patterns=[
                r"function\s+\w+\s*\([^)]*\)\s*(?:public|external)\s+view[^}]*external",
            ],
            indicators=["view", "staticcall", "getBalance", "getPrice"],
            severity=ThreatSeverity.HIGH,
            first_seen="2022-04-01",
            references=[
                "https://chainsecurity.com/curve-lp-oracle-manipulation-post-mortem/",
            ],
        ),
        ExploitPattern(
            name="Bridge Replay Attack",
            category=ThreatCategory.BRIDGE,
            description="Cross-chain message replay or verification bypass",
            code_patterns=[
                r"executeMessage\s*\([^)]*\)(?![^}]*processed)",
                r"verifyProof\s*\([^)]*\)(?![^}]*nonce)",
            ],
            indicators=["bridge", "relay", "message", "proof", "verify"],
            severity=ThreatSeverity.CRITICAL,
            first_seen="2021-08-01",
            references=[
                "https://rekt.news/wormhole-rekt/",
            ],
        ),
    ]

    # Historical incidents database
    HISTORICAL_INCIDENTS: List[HistoricalIncident] = [
        HistoricalIncident(
            name="The DAO Hack",
            date="2016-06-17",
            protocol="The DAO",
            category=ThreatCategory.REENTRANCY,
            loss_amount=60000000,
            description="Recursive call vulnerability drained 3.6M ETH",
            attack_vector="Reentrancy in splitDAO function",
            lessons_learned=[
                "Always update state before external calls",
                "Use reentrancy guards",
                "Follow checks-effects-interactions pattern",
            ],
            references=["https://blog.ethereum.org/2016/06/17/critical-update-re-dao-vulnerability"],
        ),
        HistoricalIncident(
            name="Cream Finance Flash Loan Attack",
            date="2021-10-27",
            protocol="Cream Finance",
            category=ThreatCategory.FLASH_LOAN,
            loss_amount=130000000,
            description="Flash loan used to manipulate yUSD price oracle",
            attack_vector="Oracle manipulation via flash loan",
            lessons_learned=[
                "Use TWAP oracles instead of spot prices",
                "Implement price deviation checks",
                "Limit exposure per transaction",
            ],
            references=["https://medium.com/cream-finance/c-r-e-a-m-finance-post-mortem-ae"],
        ),
        HistoricalIncident(
            name="Ronin Bridge Hack",
            date="2022-03-23",
            protocol="Ronin Network",
            category=ThreatCategory.ACCESS_CONTROL,
            loss_amount=625000000,
            description="Validator private keys compromised",
            attack_vector="Social engineering and validator compromise",
            lessons_learned=[
                "Increase validator set size",
                "Implement monitoring for large withdrawals",
                "Use hardware security modules",
            ],
            references=["https://roninblockchain.substack.com/p/community-alert-ronin-validators"],
        ),
        HistoricalIncident(
            name="Wormhole Bridge Hack",
            date="2022-02-02",
            protocol="Wormhole",
            category=ThreatCategory.BRIDGE,
            loss_amount=326000000,
            description="Signature verification bypass in bridge",
            attack_vector="Spoofed guardian signatures",
            lessons_learned=[
                "Verify all signature components",
                "Use multiple verification layers",
                "Implement rate limiting",
            ],
            references=["https://rekt.news/wormhole-rekt/"],
        ),
        HistoricalIncident(
            name="Nomad Bridge Hack",
            date="2022-08-01",
            protocol="Nomad",
            category=ThreatCategory.LOGIC_ERROR,
            loss_amount=190000000,
            description="Trusted root set to zero allowing anyone to drain",
            attack_vector="Initialization bug in upgrade",
            lessons_learned=[
                "Extensive testing for upgrades",
                "Validate critical state after initialization",
                "Implement pause mechanisms",
            ],
            references=["https://rekt.news/nomad-rekt/"],
        ),
        HistoricalIncident(
            name="Parity Wallet Freeze",
            date="2017-11-06",
            protocol="Parity Multisig",
            category=ThreatCategory.ACCESS_CONTROL,
            loss_amount=280000000,
            description="Library contract killed, freezing all dependent wallets",
            attack_vector="Unprotected initWallet function",
            lessons_learned=[
                "Protect initialization functions",
                "Avoid selfdestruct in shared code",
                "Use proxies carefully",
            ],
            references=["https://github.com/paritytech/parity-ethereum/issues/6995"],
        ),
        HistoricalIncident(
            name="Euler Finance Exploit",
            date="2023-03-13",
            protocol="Euler Finance",
            category=ThreatCategory.LOGIC_ERROR,
            loss_amount=197000000,
            description="Flash loan attack exploiting donation mechanism",
            attack_vector="Donate function manipulation + liquidation",
            lessons_learned=[
                "Review all fund flow paths",
                "Test edge cases in lending logic",
                "Implement circuit breakers",
            ],
            references=["https://www.euler.finance/blog/euler-exploit-post-mortem"],
        ),
        HistoricalIncident(
            name="Beanstalk Governance Attack",
            date="2022-04-17",
            protocol="Beanstalk",
            category=ThreatCategory.GOVERNANCE,
            loss_amount=182000000,
            description="Flash loan used to gain governance control",
            attack_vector="Flash loan voting power manipulation",
            lessons_learned=[
                "Use voting snapshots from past blocks",
                "Implement vote escrow mechanisms",
                "Add timelock for proposals",
            ],
            references=["https://bean.money/blog/beanstalk-governance-exploit"],
        ),
    ]

    def __init__(self) -> None:
        """Initialize the threat intelligence engine."""
        self.matches: List[ThreatMatch] = []
        self.alerts: List[ThreatAlert] = []

    def analyze(self, code: str, file_path: str = "") -> List[ThreatMatch]:
        """Analyze code against known threat patterns.

        Args:
            code: Source code to analyze
            file_path: Optional file path for reporting

        Returns:
            List of threat matches
        """
        self.matches = []

        for pattern in self.KNOWN_PATTERNS:
            matches = self._match_pattern(code, pattern)
            self.matches.extend(matches)

        # Sort by risk score
        self.matches.sort(key=lambda m: m.risk_score, reverse=True)

        return self.matches

    def _match_pattern(self, code: str, pattern: ExploitPattern) -> List[ThreatMatch]:
        """Match a single pattern against code."""
        matches = []
        lines = code.split("\n")

        for regex in pattern.code_patterns:
            try:
                for match in re.finditer(regex, code, re.MULTILINE | re.IGNORECASE):
                    line_num = code[: match.start()].count("\n") + 1
                    start_line = max(0, line_num - 2)
                    end_line = min(len(lines), line_num + 2)
                    matched_code = "\n".join(lines[start_line:end_line])

                    # Calculate confidence
                    confidence = self._calculate_confidence(code, pattern, match)

                    # Find similar historical incidents
                    similar = self._find_similar_incidents(pattern.category)

                    # Calculate risk score
                    risk_score = self._calculate_risk_score(pattern, confidence, similar)

                    # Generate recommendations
                    recommendations = self._generate_recommendations(pattern, similar)

                    threat_match = ThreatMatch(
                        pattern=pattern,
                        confidence=confidence,
                        matched_code=matched_code,
                        line_number=line_num,
                        similar_incidents=similar,
                        risk_score=risk_score,
                        recommendations=recommendations,
                    )
                    matches.append(threat_match)
            except re.error:
                continue

        return matches

    def _calculate_confidence(self, code: str, pattern: ExploitPattern, match: re.Match) -> float:
        """Calculate confidence score for a match."""
        confidence = 0.6  # Base confidence

        # Check for indicators
        indicators_found = sum(1 for ind in pattern.indicators if ind.lower() in code.lower())
        confidence += min(0.2, indicators_found * 0.05)

        # Check for mitigations
        mitigations = ["ReentrancyGuard", "nonReentrant", "onlyOwner", "require", "assert"]
        context_start = max(0, match.start() - 500)
        context_end = min(len(code), match.end() + 500)
        context = code[context_start:context_end]

        for mitigation in mitigations:
            if mitigation in context:
                confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def _find_similar_incidents(self, category: ThreatCategory) -> List[HistoricalIncident]:
        """Find historical incidents of the same category."""
        return [inc for inc in self.HISTORICAL_INCIDENTS if inc.category == category]

    def _calculate_risk_score(self, pattern: ExploitPattern, confidence: float, incidents: List[HistoricalIncident]) -> int:
        """Calculate risk score based on pattern, confidence, and history."""
        score = 0

        # Base score from severity
        severity_scores = {
            ThreatSeverity.CRITICAL: 70,
            ThreatSeverity.HIGH: 50,
            ThreatSeverity.MEDIUM: 30,
            ThreatSeverity.LOW: 10,
        }
        score += severity_scores.get(pattern.severity, 20)

        # Adjust by confidence
        score = int(score * confidence)

        # Boost if there are historical incidents
        if incidents:
            total_loss = sum(inc.loss_amount for inc in incidents)
            if total_loss > 100000000:
                score += 20
            elif total_loss > 10000000:
                score += 10

        return min(100, score)

    def _generate_recommendations(self, pattern: ExploitPattern, incidents: List[HistoricalIncident]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []

        # Pattern-specific recommendations
        if pattern.category == ThreatCategory.REENTRANCY:
            recommendations.extend(
                [
                    "Apply ReentrancyGuard to all functions with external calls",
                    "Follow checks-effects-interactions pattern",
                    "Update state before external calls",
                ]
            )
        elif pattern.category == ThreatCategory.FLASH_LOAN:
            recommendations.extend(
                [
                    "Use TWAP oracles with at least 30-minute window",
                    "Implement price deviation checks",
                    "Add transaction delay for large operations",
                ]
            )
        elif pattern.category == ThreatCategory.ACCESS_CONTROL:
            recommendations.extend(
                [
                    "Add access control modifiers to sensitive functions",
                    "Use OpenZeppelin AccessControl for role management",
                    "Implement multi-sig for critical operations",
                ]
            )
        elif pattern.category == ThreatCategory.GOVERNANCE:
            recommendations.extend(
                [
                    "Use voting power snapshots from past blocks",
                    "Implement vote escrow (veToken) mechanism",
                    "Add timelock for proposal execution",
                ]
            )

        # Add lessons from historical incidents
        for incident in incidents[:2]:  # Top 2 relevant incidents
            for lesson in incident.lessons_learned[:2]:  # Top 2 lessons
                if lesson not in recommendations:
                    recommendations.append(f"[From {incident.name}] {lesson}")

        return recommendations

    def get_threat_summary(self) -> Dict:
        """Get summary of detected threats."""
        if not self.matches:
            return {"total_threats": 0, "risk_level": "low"}

        critical = sum(1 for m in self.matches if m.pattern.severity == ThreatSeverity.CRITICAL)
        high = sum(1 for m in self.matches if m.pattern.severity == ThreatSeverity.HIGH)

        if critical > 0:
            risk_level = "critical"
        elif high > 0:
            risk_level = "high"
        else:
            risk_level = "medium"

        total_historical_loss = sum(sum(inc.loss_amount for inc in m.similar_incidents) for m in self.matches)

        return {
            "total_threats": len(self.matches),
            "critical_count": critical,
            "high_count": high,
            "risk_level": risk_level,
            "highest_risk_score": max(m.risk_score for m in self.matches) if self.matches else 0,
            "similar_historical_loss": total_historical_loss,
            "categories": list(set(m.pattern.category.value for m in self.matches)),
        }

    def get_historical_context(self, category: ThreatCategory) -> Dict:
        """Get historical context for a threat category."""
        incidents = self._find_similar_incidents(category)

        if not incidents:
            return {"category": category.value, "incidents": 0, "total_loss": 0}

        return {
            "category": category.value,
            "incidents": len(incidents),
            "total_loss": sum(inc.loss_amount for inc in incidents),
            "largest_incident": max(incidents, key=lambda i: i.loss_amount).name,
            "most_recent": max(incidents, key=lambda i: i.date).name,
            "common_lessons": self._get_common_lessons(incidents),
        }

    def _get_common_lessons(self, incidents: List[HistoricalIncident]) -> List[str]:
        """Extract common lessons from incidents."""
        all_lessons = []
        for inc in incidents:
            all_lessons.extend(inc.lessons_learned)

        # Count occurrences
        lesson_counts: Dict[str, int] = {}
        for lesson in all_lessons:
            lesson_counts[lesson] = lesson_counts.get(lesson, 0) + 1

        # Return most common
        sorted_lessons = sorted(lesson_counts.items(), key=lambda x: x[1], reverse=True)
        return [lesson for lesson, _ in sorted_lessons[:5]]

    def create_alert(self, match: ThreatMatch) -> ThreatAlert:
        """Create a monitoring alert for a threat match."""
        alert = ThreatAlert(
            alert_id=f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{match.pattern.category.value}",
            timestamp=datetime.now(),
            threat_category=match.pattern.category,
            severity=match.pattern.severity,
            title=f"Potential {match.pattern.name} Detected",
            description=match.pattern.description,
            affected_code=match.matched_code[:200],
            recommended_action=match.recommendations[0] if match.recommendations else "Review code manually",
        )
        self.alerts.append(alert)
        return alert

    def to_json(self) -> List[Dict]:
        """Export matches as JSON-serializable list."""
        return [
            {
                "pattern_name": m.pattern.name,
                "category": m.pattern.category.value,
                "severity": m.pattern.severity.value,
                "confidence": m.confidence,
                "line_number": m.line_number,
                "risk_score": m.risk_score,
                "similar_incidents": [{"name": i.name, "loss": i.loss_amount} for i in m.similar_incidents],
                "recommendations": m.recommendations,
            }
            for m in self.matches
        ]
