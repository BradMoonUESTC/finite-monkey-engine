"""Advanced Flash Loan Oracle Manipulation Detector.

This module provides specialized detection for flash loan oracle manipulation
attacks, including price manipulation, profit extraction, and attack path analysis.
"""

import re
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Set


class OracleType(Enum):
    """Types of price oracles."""

    CHAINLINK = "chainlink"
    UNISWAP_V2_SPOT = "uniswap_v2_spot"
    UNISWAP_V3_TWAP = "uniswap_v3_twap"
    CURVE_SPOT = "curve_spot"
    BALANCER_SPOT = "balancer_spot"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class FlashLoanProvider(Enum):
    """Flash loan providers."""

    AAVE_V2 = "aave_v2"
    AAVE_V3 = "aave_v3"
    DYDX = "dydx"
    UNISWAP_V2 = "uniswap_v2"
    UNISWAP_V3 = "uniswap_v3"
    BALANCER = "balancer"
    MAKER = "maker"
    EULER = "euler"
    UNKNOWN = "unknown"


class ManipulabilityLevel(Enum):
    """Oracle manipulability assessment levels."""

    HIGH = "high"  # Easily manipulated (spot prices)
    MEDIUM = "medium"  # Requires significant capital
    LOW = "low"  # TWAP with long window
    MINIMAL = "minimal"  # Chainlink or similar


@dataclass
class FlashLoanEntry:
    """Detected flash loan entry point."""

    provider: FlashLoanProvider
    function_name: str
    line_number: int
    code_snippet: str
    callback_function: Optional[str] = None


@dataclass
class OracleRead:
    """Detected oracle price read."""

    oracle_type: OracleType
    function_call: str
    line_number: int
    code_snippet: str
    manipulability: ManipulabilityLevel = ManipulabilityLevel.MEDIUM
    twap_window: Optional[int] = None  # TWAP window in seconds


@dataclass
class ProfitMechanism:
    """Identified profit extraction mechanism."""

    mechanism_type: str
    description: str
    affected_function: str
    line_number: int
    estimated_impact: str


@dataclass
class AttackPath:
    """Complete attack path analysis."""

    flash_loan_entry: FlashLoanEntry
    oracle_reads: List[OracleRead]
    profit_mechanisms: List[ProfitMechanism]
    is_viable: bool
    viability_reason: str
    estimated_profit: str
    required_capital: str
    complexity: str  # low, medium, high


@dataclass
class TaintedVariable:
    """Variable that is tainted by oracle data."""

    name: str
    source_oracle: OracleRead
    propagation_path: List[str] = field(default_factory=list)
    reaches_sink: bool = False
    sink_description: Optional[str] = None


@dataclass
class FlashLoanFinding:
    """A flash loan oracle manipulation finding."""

    title: str
    severity: str
    description: str
    attack_paths: List[AttackPath]
    affected_oracles: List[OracleRead]
    tainted_variables: List[TaintedVariable]
    poc_template: str
    mitigation: str
    estimated_max_loss: str


class FlashLoanOracleDetector:
    """Detect flash loan oracle manipulation vulnerabilities.

    This detector identifies:
    - Flash loan entry points (callbacks, provider calls)
    - Oracle price reads (Chainlink, Uniswap TWAP, DEX spot prices, custom oracles)
    - Oracle manipulability based on type
    - Data flow from oracle to value-affecting operations
    - Profit mechanisms (borrow at manipulated price, liquidation abuse, arbitrage)
    - Economic impact and viability
    - Proof-of-concept code generation
    """

    # Flash loan provider patterns
    FLASH_LOAN_PATTERNS = {
        FlashLoanProvider.AAVE_V2: [
            r"flashLoan\s*\(",
            r"IFlashLoanReceiver",
            r"executeOperation\s*\([^)]*assets",
        ],
        FlashLoanProvider.AAVE_V3: [
            r"flashLoan\s*\(",
            r"IFlashLoanSimpleReceiver",
            r"executeOperation\s*\([^)]*asset",
        ],
        FlashLoanProvider.DYDX: [
            r"SoloMargin",
            r"callFunction\s*\(",
            r"AccountInfo",
        ],
        FlashLoanProvider.UNISWAP_V2: [
            r"uniswapV2Call\s*\(",
            r"IUniswapV2Callee",
        ],
        FlashLoanProvider.UNISWAP_V3: [
            r"uniswapV3FlashCallback\s*\(",
            r"flash\s*\(",
            r"IUniswapV3FlashCallback",
        ],
        FlashLoanProvider.BALANCER: [
            r"flashLoan\s*\(",
            r"receiveFlashLoan\s*\(",
            r"IFlashLoanRecipient",
        ],
        FlashLoanProvider.MAKER: [
            r"daiJoin",
            r"flashLoan\s*\(",
        ],
        FlashLoanProvider.EULER: [
            r"flashLoan\s*\(",
            r"onFlashLoan\s*\(",
        ],
    }

    # Oracle type patterns
    ORACLE_PATTERNS = {
        OracleType.CHAINLINK: [
            r"latestRoundData\s*\(",
            r"latestAnswer\s*\(",
            r"AggregatorV3Interface",
            r"priceFeed\.",
        ],
        OracleType.UNISWAP_V2_SPOT: [
            r"getReserves\s*\(",
            r"IUniswapV2Pair",
            r"reserve0\s*\*\s*\w+\s*/\s*reserve1",
        ],
        OracleType.UNISWAP_V3_TWAP: [
            r"observe\s*\(",
            r"slot0\s*\(",
            r"sqrtPriceX96",
            r"tickCumulatives",
        ],
        OracleType.CURVE_SPOT: [
            r"get_dy\s*\(",
            r"get_virtual_price\s*\(",
            r"ICurvePool",
        ],
        OracleType.BALANCER_SPOT: [
            r"getPoolTokens\s*\(",
            r"getRate\s*\(",
            r"IBalancerVault",
        ],
        OracleType.CUSTOM: [
            r"getPrice\s*\(",
            r"fetchPrice\s*\(",
            r"priceOracle\.",
            r"\.price\s*\(",
        ],
    }

    # Profit mechanism patterns
    PROFIT_PATTERNS = {
        "borrow_manipulation": [
            r"borrow\s*\(",
            r"collateral.*price",
            r"borrowAllowed\s*\(",
        ],
        "liquidation_abuse": [
            r"liquidate\s*\(",
            r"liquidateBorrow\s*\(",
            r"isLiquidatable",
        ],
        "swap_arbitrage": [
            r"swap\s*\(",
            r"swapExact",
            r"getAmountOut\s*\(",
        ],
        "vault_manipulation": [
            r"deposit\s*\(",
            r"withdraw\s*\(",
            r"totalAssets\s*\(",
            r"convertToShares\s*\(",
        ],
        "reward_claiming": [
            r"claim\s*\(",
            r"getReward\s*\(",
            r"earned\s*\(",
        ],
    }

    # Value-affecting sinks
    VALUE_SINKS = [
        r"transfer\s*\(",
        r"transferFrom\s*\(",
        r"mint\s*\(",
        r"burn\s*\(",
        r"borrow\s*\(",
        r"repay\s*\(",
        r"deposit\s*\(",
        r"withdraw\s*\(",
        r"liquidate\s*\(",
    ]

    def __init__(self) -> None:
        """Initialize the flash loan oracle detector."""
        self.flash_loan_entries: List[FlashLoanEntry] = []
        self.oracle_reads: List[OracleRead] = []
        self.profit_mechanisms: List[ProfitMechanism] = []
        self.attack_paths: List[AttackPath] = []
        self.tainted_variables: List[TaintedVariable] = []
        self.findings: List[FlashLoanFinding] = []

    def analyze(self, code: str, file_path: str = "") -> List[FlashLoanFinding]:
        """Analyze code for flash loan oracle manipulation vulnerabilities.

        Args:
            code: Source code to analyze
            file_path: Optional file path for reporting

        Returns:
            List of flash loan manipulation findings
        """
        self._reset()

        # Step 1: Detect flash loan entry points
        self._detect_flash_loan_entries(code)

        # Step 2: Identify oracle price reads
        self._detect_oracle_reads(code)

        # Step 3: Assess oracle manipulability
        self._assess_manipulability()

        # Step 4: Find profit mechanisms
        self._detect_profit_mechanisms(code)

        # Step 5: Perform taint analysis
        self._perform_taint_analysis(code)

        # Step 6: Build attack paths
        self._build_attack_paths()

        # Step 7: Calculate economic impact
        self._calculate_economic_impact()

        # Step 8: Generate findings
        self._generate_findings(file_path)

        return self.findings

    def _reset(self) -> None:
        """Reset all detection state."""
        self.flash_loan_entries = []
        self.oracle_reads = []
        self.profit_mechanisms = []
        self.attack_paths = []
        self.tainted_variables = []
        self.findings = []

    def _detect_flash_loan_entries(self, code: str) -> None:
        """Detect flash loan entry points in code."""
        lines = code.split("\n")

        for provider, patterns in self.FLASH_LOAN_PATTERNS.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE):
                        line_num = code[: match.start()].count("\n") + 1
                        start_line = max(0, line_num - 2)
                        end_line = min(len(lines), line_num + 2)
                        snippet = "\n".join(lines[start_line:end_line])

                        # Try to find callback function
                        callback = self._find_callback_function(code, provider)

                        entry = FlashLoanEntry(
                            provider=provider,
                            function_name=match.group(0),
                            line_number=line_num,
                            code_snippet=snippet,
                            callback_function=callback,
                        )
                        self.flash_loan_entries.append(entry)
                except re.error:
                    continue

    def _find_callback_function(self, code: str, provider: FlashLoanProvider) -> Optional[str]:
        """Find the callback function for a flash loan provider."""
        callback_patterns = {
            FlashLoanProvider.AAVE_V2: r"function\s+executeOperation\s*\(",
            FlashLoanProvider.AAVE_V3: r"function\s+executeOperation\s*\(",
            FlashLoanProvider.UNISWAP_V2: r"function\s+uniswapV2Call\s*\(",
            FlashLoanProvider.UNISWAP_V3: r"function\s+uniswapV3FlashCallback\s*\(",
            FlashLoanProvider.BALANCER: r"function\s+receiveFlashLoan\s*\(",
            FlashLoanProvider.DYDX: r"function\s+callFunction\s*\(",
        }

        pattern = callback_patterns.get(provider)
        if pattern:
            match = re.search(pattern, code)
            if match:
                return match.group(0)
        return None

    def _detect_oracle_reads(self, code: str) -> None:
        """Detect oracle price reads in code."""
        lines = code.split("\n")

        for oracle_type, patterns in self.ORACLE_PATTERNS.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE):
                        line_num = code[: match.start()].count("\n") + 1
                        start_line = max(0, line_num - 2)
                        end_line = min(len(lines), line_num + 2)
                        snippet = "\n".join(lines[start_line:end_line])

                        # Check for TWAP window in Uniswap V3
                        twap_window = None
                        if oracle_type == OracleType.UNISWAP_V3_TWAP:
                            twap_window = self._extract_twap_window(code, match.start())

                        oracle_read = OracleRead(
                            oracle_type=oracle_type,
                            function_call=match.group(0),
                            line_number=line_num,
                            code_snippet=snippet,
                            twap_window=twap_window,
                        )
                        self.oracle_reads.append(oracle_read)
                except re.error:
                    continue

    def _extract_twap_window(self, code: str, position: int) -> Optional[int]:
        """Extract TWAP window from Uniswap V3 oracle code."""
        # Look for secondsAgo parameter
        context = code[max(0, position - 200) : min(len(code), position + 200)]
        window_match = re.search(r"secondsAgo\s*[=:]\s*(\d+)", context)
        if window_match:
            return int(window_match.group(1))

        # Look for interval/period parameters
        period_match = re.search(r"(?:period|interval|window)\s*[=:]\s*(\d+)", context, re.IGNORECASE)
        if period_match:
            return int(period_match.group(1))

        return None

    def _assess_manipulability(self) -> None:
        """Assess manipulability level for each oracle read."""
        for oracle in self.oracle_reads:
            if oracle.oracle_type == OracleType.CHAINLINK:
                oracle.manipulability = ManipulabilityLevel.MINIMAL
            elif oracle.oracle_type == OracleType.UNISWAP_V3_TWAP:
                if oracle.twap_window and oracle.twap_window >= 1800:  # 30+ minutes
                    oracle.manipulability = ManipulabilityLevel.LOW
                elif oracle.twap_window and oracle.twap_window >= 300:  # 5+ minutes
                    oracle.manipulability = ManipulabilityLevel.MEDIUM
                else:
                    oracle.manipulability = ManipulabilityLevel.HIGH
            elif oracle.oracle_type in [OracleType.UNISWAP_V2_SPOT, OracleType.CURVE_SPOT, OracleType.BALANCER_SPOT]:
                oracle.manipulability = ManipulabilityLevel.HIGH
            else:
                oracle.manipulability = ManipulabilityLevel.MEDIUM

    def _detect_profit_mechanisms(self, code: str) -> None:
        """Detect potential profit extraction mechanisms."""
        lines = code.split("\n")

        for mechanism_type, patterns in self.PROFIT_PATTERNS.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE):
                        line_num = code[: match.start()].count("\n") + 1

                        mechanism = ProfitMechanism(
                            mechanism_type=mechanism_type,
                            description=self._get_mechanism_description(mechanism_type),
                            affected_function=match.group(0),
                            line_number=line_num,
                            estimated_impact=self._estimate_mechanism_impact(mechanism_type),
                        )
                        self.profit_mechanisms.append(mechanism)
                except re.error:
                    continue

    def _get_mechanism_description(self, mechanism_type: str) -> str:
        """Get description for a profit mechanism type."""
        descriptions = {
            "borrow_manipulation": "Borrow assets at manipulated collateral price",
            "liquidation_abuse": "Trigger unfair liquidations through price manipulation",
            "swap_arbitrage": "Profit from artificially skewed swap rates",
            "vault_manipulation": "Manipulate vault share price for profit extraction",
            "reward_claiming": "Claim inflated rewards based on manipulated prices",
        }
        return descriptions.get(mechanism_type, "Unknown profit mechanism")

    def _estimate_mechanism_impact(self, mechanism_type: str) -> str:
        """Estimate impact for a profit mechanism type."""
        impacts = {
            "borrow_manipulation": "$100K-$10M",
            "liquidation_abuse": "$50K-$5M",
            "swap_arbitrage": "$10K-$1M",
            "vault_manipulation": "$100K-$5M",
            "reward_claiming": "$10K-$500K",
        }
        return impacts.get(mechanism_type, "$10K-$100K")

    def _perform_taint_analysis(self, code: str) -> None:
        """Perform taint analysis from oracle reads to value sinks."""
        # Simplified taint analysis - track variables that receive oracle data
        for oracle in self.oracle_reads:
            # Find variable assignment from oracle read
            context_start = max(0, code.find(oracle.function_call) - 100)
            context_end = min(len(code), code.find(oracle.function_call) + 100)
            context = code[context_start:context_end]

            # Look for variable assignment
            var_match = re.search(r"(\w+)\s*=\s*" + re.escape(oracle.function_call), context)
            if var_match:
                var_name = var_match.group(1)

                # Track if this variable reaches a value sink
                reaches_sink = False
                sink_description = None

                for sink_pattern in self.VALUE_SINKS:
                    # Check if the variable is used near a sink
                    sink_matches = list(re.finditer(sink_pattern, code))
                    for sink_match in sink_matches:
                        sink_context_start = max(0, sink_match.start() - 200)
                        sink_context_end = min(len(code), sink_match.end() + 50)
                        sink_context = code[sink_context_start:sink_context_end]

                        if var_name in sink_context:
                            reaches_sink = True
                            sink_description = sink_match.group(0)
                            break

                    if reaches_sink:
                        break

                tainted_var = TaintedVariable(
                    name=var_name,
                    source_oracle=oracle,
                    propagation_path=[var_name],
                    reaches_sink=reaches_sink,
                    sink_description=sink_description,
                )
                self.tainted_variables.append(tainted_var)

    def _build_attack_paths(self) -> None:
        """Build complete attack paths from flash loans to profit."""
        if not self.flash_loan_entries or not self.oracle_reads:
            return

        # For each flash loan entry, check if there's a viable attack path
        for flash_entry in self.flash_loan_entries:
            # Find manipulable oracles
            manipulable_oracles = [o for o in self.oracle_reads if o.manipulability in [ManipulabilityLevel.HIGH, ManipulabilityLevel.MEDIUM]]

            if not manipulable_oracles:
                continue

            # Find profit mechanisms that could benefit
            viable_mechanisms = self.profit_mechanisms.copy()

            # Check if tainted data reaches value sinks
            has_tainted_path = any(tv.reaches_sink for tv in self.tainted_variables)

            is_viable = bool(manipulable_oracles and (viable_mechanisms or has_tainted_path))

            viability_reason = ""
            if is_viable:
                viability_reason = "Manipulable oracle price flows to value-affecting operation"
            elif manipulable_oracles and not viable_mechanisms:
                viability_reason = "Manipulable oracle found but no clear profit mechanism"
                is_viable = True  # Still worth investigating
            else:
                viability_reason = "No manipulable oracles detected"

            attack_path = AttackPath(
                flash_loan_entry=flash_entry,
                oracle_reads=manipulable_oracles,
                profit_mechanisms=viable_mechanisms,
                is_viable=is_viable,
                viability_reason=viability_reason,
                estimated_profit=self._estimate_profit(manipulable_oracles, viable_mechanisms),
                required_capital=self._estimate_required_capital(manipulable_oracles),
                complexity=self._assess_complexity(flash_entry, manipulable_oracles),
            )
            self.attack_paths.append(attack_path)

    def _estimate_profit(self, oracles: List[OracleRead], mechanisms: List[ProfitMechanism]) -> str:
        """Estimate potential profit from attack."""
        if not mechanisms:
            return "$10K-$100K (estimate)"

        # Use highest impact mechanism
        high_impacts = ["borrow_manipulation", "liquidation_abuse", "vault_manipulation"]
        if any(m.mechanism_type in high_impacts for m in mechanisms):
            return "$100K-$10M+"
        return "$10K-$500K"

    def _estimate_required_capital(self, oracles: List[OracleRead]) -> str:
        """Estimate capital required to manipulate oracles."""
        if any(o.oracle_type == OracleType.UNISWAP_V2_SPOT for o in oracles):
            return "$1M-$10M (depending on pool liquidity)"
        elif any(o.oracle_type == OracleType.CURVE_SPOT for o in oracles):
            return "$5M-$50M (higher liquidity pools)"
        else:
            return "$100K-$1M (estimate)"

    def _assess_complexity(self, flash_entry: FlashLoanEntry, oracles: List[OracleRead]) -> str:
        """Assess attack complexity."""
        if flash_entry.callback_function and len(oracles) == 1:
            return "low"
        elif len(oracles) > 2:
            return "high"
        else:
            return "medium"

    def _calculate_economic_impact(self) -> None:
        """Calculate economic impact for all attack paths."""
        # Impact calculation is done during path building
        pass

    def _generate_findings(self, file_path: str) -> None:
        """Generate findings from analysis."""
        if not self.attack_paths:
            # Check if there are any oracles without flash loans
            if self.oracle_reads:
                manipulable = [o for o in self.oracle_reads if o.manipulability == ManipulabilityLevel.HIGH]
                if manipulable:
                    finding = FlashLoanFinding(
                        title="Potentially Manipulable Price Oracle",
                        severity="MEDIUM",
                        description="Contract uses price oracles that could be manipulated",
                        attack_paths=[],
                        affected_oracles=manipulable,
                        tainted_variables=self.tainted_variables,
                        poc_template="N/A - No flash loan entry point detected",
                        mitigation="Use TWAP oracles with longer windows or Chainlink price feeds",
                        estimated_max_loss="Depends on integration context",
                    )
                    self.findings.append(finding)
            return

        # Generate findings for viable attack paths
        viable_paths = [p for p in self.attack_paths if p.is_viable]

        if viable_paths:
            poc = self._generate_poc_template(viable_paths[0])

            finding = FlashLoanFinding(
                title="Flash Loan Oracle Manipulation Vulnerability",
                severity="CRITICAL" if any(p.complexity == "low" for p in viable_paths) else "HIGH",
                description="Contract is vulnerable to flash loan oracle manipulation attack",
                attack_paths=viable_paths,
                affected_oracles=[o for p in viable_paths for o in p.oracle_reads],
                tainted_variables=self.tainted_variables,
                poc_template=poc,
                mitigation=self._generate_mitigation_recommendations(viable_paths),
                estimated_max_loss=max(p.estimated_profit for p in viable_paths),
            )
            self.findings.append(finding)

    def _generate_poc_template(self, attack_path: AttackPath) -> str:
        """Generate a proof-of-concept template for an attack path."""
        flash_provider = attack_path.flash_loan_entry.provider.value
        oracle_type = attack_path.oracle_reads[0].oracle_type.value if attack_path.oracle_reads else "unknown"

        poc = f"""
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract FlashLoanAttackPOC is Test {{
    // Target contract
    address target;

    // Flash loan provider: {flash_provider}
    // Oracle type: {oracle_type}

    function setUp() public {{
        // Fork mainnet at vulnerable block
        // vm.createSelectFork(vm.rpcUrl("mainnet"), BLOCK_NUMBER);

        // Setup target contract
        target = address(0x...);
    }}

    function testFlashLoanAttack() public {{
        // Step 1: Get flash loan
        // {flash_provider} flash loan

        // Step 2: Manipulate oracle price
        // Perform large swap to move {oracle_type} price

        // Step 3: Execute profitable action
        // Call target function with manipulated price

        // Step 4: Restore price and repay flash loan
        // Swap back and repay

        // Step 5: Verify profit
        // assertGt(profit, flashLoanFee);
    }}

    // Flash loan callback
    function {attack_path.flash_loan_entry.callback_function or "executeOperation"}(...) external {{
        // Attack logic here
    }}
}}
"""
        return poc

    def _generate_mitigation_recommendations(self, attack_paths: List[AttackPath]) -> str:
        """Generate mitigation recommendations based on attack paths."""
        recommendations = []

        # Check oracle types used
        oracle_types = set()
        for path in attack_paths:
            for oracle in path.oracle_reads:
                oracle_types.add(oracle.oracle_type)

        if OracleType.UNISWAP_V2_SPOT in oracle_types:
            recommendations.append("- Replace Uniswap V2 spot price with TWAP oracle (30+ min window)")

        if OracleType.UNISWAP_V3_TWAP in oracle_types:
            recommendations.append("- Increase TWAP window to at least 30 minutes")

        if OracleType.CURVE_SPOT in oracle_types or OracleType.BALANCER_SPOT in oracle_types:
            recommendations.append("- Use Chainlink oracles instead of DEX spot prices")

        # General recommendations
        recommendations.extend(
            [
                "- Implement price deviation checks (max % change per block)",
                "- Add liquidity depth verification before accepting prices",
                "- Consider using multiple oracle sources with median pricing",
                "- Implement cooldown periods for large value operations",
            ]
        )

        return "\n".join(recommendations)

    def get_summary(self) -> Dict:
        """Get a summary of the analysis."""
        return {
            "flash_loan_entries": len(self.flash_loan_entries),
            "oracle_reads": len(self.oracle_reads),
            "manipulable_oracles": len([o for o in self.oracle_reads if o.manipulability == ManipulabilityLevel.HIGH]),
            "profit_mechanisms": len(self.profit_mechanisms),
            "viable_attack_paths": len([p for p in self.attack_paths if p.is_viable]),
            "tainted_variables_reaching_sinks": len([t for t in self.tainted_variables if t.reaches_sink]),
            "findings": len(self.findings),
        }

    def to_json(self) -> List[Dict]:
        """Export findings as JSON-serializable list."""
        return [
            {
                "title": f.title,
                "severity": f.severity,
                "description": f.description,
                "attack_paths_count": len(f.attack_paths),
                "affected_oracles": [{"type": o.oracle_type.value, "manipulability": o.manipulability.value} for o in f.affected_oracles],
                "poc_template": f.poc_template,
                "mitigation": f.mitigation,
                "estimated_max_loss": f.estimated_max_loss,
            }
            for f in self.findings
        ]
