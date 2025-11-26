"""Economic Impact Analyzer for Smart Contract Vulnerabilities.

This module calculates economic feasibility and impact of various
vulnerability types to help prioritize findings.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional


class VulnerabilityType(Enum):
    """Types of vulnerabilities for economic analysis."""

    FLASH_LOAN = "flash_loan"
    GOVERNANCE = "governance"
    REENTRANCY = "reentrancy"
    PRICE_MANIPULATION = "price_manipulation"
    ACCESS_CONTROL = "access_control"
    INTEGER_OVERFLOW = "integer_overflow"
    SIGNATURE_REPLAY = "signature_replay"
    ORACLE_MANIPULATION = "oracle_manipulation"
    FRONT_RUNNING = "front_running"
    LIQUIDATION = "liquidation"
    VAULT_INFLATION = "vault_inflation"
    BRIDGE = "bridge"


class AttackComplexity(Enum):
    """Complexity levels for attacks."""

    TRIVIAL = "trivial"  # Script kiddie level
    LOW = "low"  # Moderate skill required
    MEDIUM = "medium"  # Experienced developer
    HIGH = "high"  # Expert level
    EXPERT = "expert"  # Nation-state level


class RiskLevel(Enum):
    """Risk level classifications."""

    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # High priority fix
    MEDIUM = "medium"  # Should be fixed soon
    LOW = "low"  # Fix when possible
    INFORMATIONAL = "informational"  # Awareness only


@dataclass
class ProtocolMetrics:
    """Protocol-level metrics for impact calculation."""

    total_value_locked: float = 0.0  # TVL in USD
    daily_volume: float = 0.0  # Daily trading volume
    liquidity_depth: float = 0.0  # Available liquidity
    token_supply: float = 0.0  # Total token supply
    governance_token_price: float = 0.0  # Price of governance token
    flash_loan_available: float = 0.0  # Available flash loan capital
    protocol_fee: float = 0.0  # Protocol fee percentage


@dataclass
class EconomicImpact:
    """Economic impact assessment for a vulnerability."""

    vulnerability_type: VulnerabilityType
    max_potential_loss: float
    attack_capital_required: float
    estimated_profit: float
    gas_cost_estimate: float
    flash_loan_fees: float
    is_profitable: bool
    profitability_margin: float
    risk_score: int  # 0-100
    attack_complexity: AttackComplexity
    time_to_execute: str  # "instant", "minutes", "hours", "days"
    detection_likelihood: str  # "low", "medium", "high"
    mitigation_cost: str  # Estimated cost to fix
    confidence: float  # 0.0 to 1.0


@dataclass
class AttackScenario:
    """A specific attack scenario with economic details."""

    name: str
    description: str
    steps: List[str]
    required_capital: float
    expected_profit: float
    success_probability: float
    prerequisites: List[str]
    detection_risk: str


class EconomicImpactAnalyzer:
    """Calculate economic feasibility and impact of vulnerabilities.

    Analyzes:
    - Flash Loan attacks (capital required, flash loan fees, arbitrage profit)
    - Governance attacks (tokens needed, drainable value, timelock effects)
    - Reentrancy attacks (minimal capital, max drain potential)
    - Price manipulation (pool size impact, capital requirements)
    - Access control bypasses (low capital, high impact)
    - Integer overflow/underflow (unlimited minting potential)

    Outputs:
    - Max potential loss
    - Attack capital required
    - Estimated profit
    - Gas cost estimate
    - Flash loan fees
    - Profitability assessment
    - Risk score (0-100)
    - Attack complexity
    - Time to execute
    - Detection likelihood
    """

    # Flash loan fee rates by provider (in basis points)
    FLASH_LOAN_FEES = {
        "aave_v2": 9,  # 0.09%
        "aave_v3": 5,  # 0.05% (can be 0 for some assets)
        "dydx": 0,  # Free (2 wei)
        "uniswap_v2": 30,  # 0.3%
        "uniswap_v3": 1,  # Depends on pool
        "balancer": 0,  # Free protocol level
        "maker": 0,  # Free for DAI
    }

    # Gas costs for common operations (in gas units)
    GAS_COSTS = {
        "flash_loan": 300000,
        "swap": 150000,
        "transfer": 21000,
        "erc20_transfer": 65000,
        "contract_call": 50000,
        "storage_write": 20000,
    }

    # Default gas price in Gwei
    DEFAULT_GAS_PRICE = 30

    # Profit extraction rates for different attack scenarios
    # These are based on historical exploit data and economic modeling
    PROFIT_EXTRACTION_RATES = {
        # Governance attacks with timelock: ~30% extraction due to price risk,
        # execution delays, and potential community response
        "governance_with_timelock": 0.3,
        # Governance attacks without timelock: ~80% extraction, limited only by
        # slippage and detection risk
        "governance_instant": 0.8,
        # Flash loan attacks: ~50% due to MEV competition and gas costs
        "flash_loan": 0.5,
        # Reentrancy: Nearly full extraction possible
        "reentrancy": 0.95,
        # Price manipulation: Depends on liquidity depth
        "price_manipulation": 0.7,
    }

    def __init__(self, protocol_metrics: Optional[ProtocolMetrics] = None) -> None:
        """Initialize the economic impact analyzer.

        Args:
            protocol_metrics: Optional protocol-specific metrics
        """
        self.metrics = protocol_metrics or ProtocolMetrics()

    def analyze_vulnerability(self, vuln_type: VulnerabilityType, context: Optional[Dict] = None) -> EconomicImpact:
        """Analyze economic impact of a vulnerability.

        Args:
            vuln_type: Type of vulnerability
            context: Additional context for analysis

        Returns:
            Economic impact assessment
        """
        context = context or {}

        # Route to specific analyzer
        analyzers = {
            VulnerabilityType.FLASH_LOAN: self._analyze_flash_loan,
            VulnerabilityType.GOVERNANCE: self._analyze_governance,
            VulnerabilityType.REENTRANCY: self._analyze_reentrancy,
            VulnerabilityType.PRICE_MANIPULATION: self._analyze_price_manipulation,
            VulnerabilityType.ACCESS_CONTROL: self._analyze_access_control,
            VulnerabilityType.INTEGER_OVERFLOW: self._analyze_integer_overflow,
            VulnerabilityType.ORACLE_MANIPULATION: self._analyze_oracle_manipulation,
            VulnerabilityType.FRONT_RUNNING: self._analyze_front_running,
            VulnerabilityType.LIQUIDATION: self._analyze_liquidation,
            VulnerabilityType.VAULT_INFLATION: self._analyze_vault_inflation,
            VulnerabilityType.BRIDGE: self._analyze_bridge,
        }

        analyzer = analyzers.get(vuln_type, self._analyze_generic)
        return analyzer(context)

    def _analyze_flash_loan(self, context: Dict) -> EconomicImpact:
        """Analyze flash loan attack economics."""
        # Flash loan attacks typically target oracle manipulation or arbitrage
        tvl = context.get("tvl", self.metrics.total_value_locked) or 1000000
        manipulable_amount = context.get("manipulable_amount", tvl * 0.1)

        # Capital required is the flash loan amount (free if using dYdX)
        capital_required = 0  # Flash loans are capital-free

        # Max extractable is typically a percentage of TVL
        max_loss = min(manipulable_amount, tvl * 0.5)

        # Flash loan fees
        flash_loan_amount = manipulable_amount * 2  # Need 2x to move price
        fees = flash_loan_amount * self.FLASH_LOAN_FEES["aave_v3"] / 10000

        # Gas costs for flash loan + swaps
        gas_units = self.GAS_COSTS["flash_loan"] + 4 * self.GAS_COSTS["swap"]
        gas_cost = gas_units * self.DEFAULT_GAS_PRICE * 1e-9 * 2000  # ETH price estimate

        estimated_profit = max_loss * 0.5 - fees - gas_cost
        is_profitable = estimated_profit > 0

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.FLASH_LOAN,
            max_potential_loss=max_loss,
            attack_capital_required=capital_required,
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=fees,
            is_profitable=is_profitable,
            profitability_margin=estimated_profit / max_loss if max_loss > 0 else 0,
            risk_score=min(100, int((max_loss / 1000000) * 50 + 50)) if is_profitable else 30,
            attack_complexity=AttackComplexity.MEDIUM,
            time_to_execute="instant",
            detection_likelihood="high",
            mitigation_cost="$5K-$20K (TWAP implementation)",
            confidence=0.7,
        )

    def _analyze_governance(self, context: Dict) -> EconomicImpact:
        """Analyze governance attack economics."""
        gov_token_supply = context.get("token_supply", self.metrics.token_supply) or 1000000
        token_price = context.get("token_price", self.metrics.governance_token_price) or 10
        treasury_value = context.get("treasury_value", self.metrics.total_value_locked * 0.1) or 100000

        # Capital needed to control governance (typically 50%+ for quorum)
        quorum_percentage = context.get("quorum", 0.5)
        tokens_needed = gov_token_supply * quorum_percentage
        capital_required = tokens_needed * token_price

        # For flash loan governance attack
        flash_loan_capital = 0  # Can borrow tokens
        flash_loan_fees = capital_required * self.FLASH_LOAN_FEES["aave_v3"] / 10000

        max_loss = treasury_value
        gas_cost = (self.GAS_COSTS["contract_call"] * 5) * self.DEFAULT_GAS_PRICE * 1e-9 * 2000

        # Governance attacks often have timelocks
        timelock = context.get("timelock_days", 2)
        if timelock > 0:
            # Timelock reduces profitability due to token price risk
            extraction_rate = self.PROFIT_EXTRACTION_RATES["governance_with_timelock"]
            estimated_profit = max_loss * extraction_rate - flash_loan_fees - gas_cost
            attack_complexity = AttackComplexity.HIGH
            time_to_execute = f"{timelock} days"
        else:
            extraction_rate = self.PROFIT_EXTRACTION_RATES["governance_instant"]
            estimated_profit = max_loss * extraction_rate - flash_loan_fees - gas_cost
            attack_complexity = AttackComplexity.MEDIUM
            time_to_execute = "instant"

        is_profitable = estimated_profit > 0

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.GOVERNANCE,
            max_potential_loss=max_loss,
            attack_capital_required=flash_loan_capital,
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=flash_loan_fees,
            is_profitable=is_profitable,
            profitability_margin=estimated_profit / max_loss if max_loss > 0 else 0,
            risk_score=min(100, int((max_loss / 1000000) * 40 + 30)) if is_profitable else 20,
            attack_complexity=attack_complexity,
            time_to_execute=time_to_execute,
            detection_likelihood="medium",
            mitigation_cost="$10K-$50K (vote escrow, snapshots)",
            confidence=0.6,
        )

    def _analyze_reentrancy(self, context: Dict) -> EconomicImpact:
        """Analyze reentrancy attack economics."""
        contract_balance = context.get("contract_balance", self.metrics.total_value_locked) or 100000

        # Reentrancy can drain entire contract
        max_loss = contract_balance

        # Minimal capital required (just gas)
        capital_required = 100  # Small amount to trigger

        # Gas costs for multiple calls
        reentry_depth = context.get("reentry_depth", 10)
        gas_cost = reentry_depth * self.GAS_COSTS["contract_call"] * self.DEFAULT_GAS_PRICE * 1e-9 * 2000

        estimated_profit = max_loss - capital_required - gas_cost
        is_profitable = estimated_profit > 0

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.REENTRANCY,
            max_potential_loss=max_loss,
            attack_capital_required=capital_required,
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=0,
            is_profitable=is_profitable,
            profitability_margin=estimated_profit / max_loss if max_loss > 0 else 0,
            risk_score=min(100, int((max_loss / 100000) * 60 + 40)) if is_profitable else 50,
            attack_complexity=AttackComplexity.LOW,
            time_to_execute="instant",
            detection_likelihood="medium",
            mitigation_cost="$2K-$10K (ReentrancyGuard)",
            confidence=0.85,
        )

    def _analyze_price_manipulation(self, context: Dict) -> EconomicImpact:
        """Analyze price manipulation attack economics."""
        pool_liquidity = context.get("pool_liquidity", self.metrics.liquidity_depth) or 1000000

        # Capital needed to move price significantly (Uniswap formula)
        target_price_impact = context.get("price_impact", 0.1)  # 10% price move
        capital_required = pool_liquidity * target_price_impact

        # Can use flash loans
        flash_loan_fees = capital_required * self.FLASH_LOAN_FEES["aave_v3"] / 10000

        # Profit depends on affected position
        affected_position = context.get("affected_position", pool_liquidity * 0.05)
        max_loss = affected_position * target_price_impact * 2  # Doubled due to round trip

        gas_cost = 4 * self.GAS_COSTS["swap"] * self.DEFAULT_GAS_PRICE * 1e-9 * 2000

        estimated_profit = max_loss * 0.7 - flash_loan_fees - gas_cost
        is_profitable = estimated_profit > 0

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.PRICE_MANIPULATION,
            max_potential_loss=max_loss,
            attack_capital_required=0,  # Flash loan
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=flash_loan_fees,
            is_profitable=is_profitable,
            profitability_margin=estimated_profit / max_loss if max_loss > 0 else 0,
            risk_score=min(100, int((max_loss / 500000) * 50 + 30)) if is_profitable else 25,
            attack_complexity=AttackComplexity.MEDIUM,
            time_to_execute="instant",
            detection_likelihood="high",
            mitigation_cost="$5K-$30K (TWAP, multiple oracles)",
            confidence=0.7,
        )

    def _analyze_access_control(self, context: Dict) -> EconomicImpact:
        """Analyze access control bypass economics."""
        # Access control issues typically expose entire contract value
        contract_value = context.get("contract_value", self.metrics.total_value_locked) or 500000

        max_loss = contract_value
        capital_required = 0  # Just gas needed

        gas_cost = self.GAS_COSTS["contract_call"] * self.DEFAULT_GAS_PRICE * 1e-9 * 2000
        estimated_profit = max_loss - gas_cost

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.ACCESS_CONTROL,
            max_potential_loss=max_loss,
            attack_capital_required=capital_required,
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=0,
            is_profitable=True,
            profitability_margin=0.99,  # Almost pure profit
            risk_score=min(100, int((max_loss / 100000) * 70 + 30)),
            attack_complexity=AttackComplexity.TRIVIAL,
            time_to_execute="instant",
            detection_likelihood="low",
            mitigation_cost="$1K-$5K (add modifiers)",
            confidence=0.9,
        )

    def _analyze_integer_overflow(self, context: Dict) -> EconomicImpact:
        """Analyze integer overflow economics."""
        token_supply = context.get("token_supply", self.metrics.token_supply) or 1000000000
        token_price = context.get("token_price", 1.0)

        # Overflow could potentially mint unlimited tokens
        max_loss = token_supply * token_price  # Could destroy token value

        capital_required = 0
        gas_cost = self.GAS_COSTS["contract_call"] * self.DEFAULT_GAS_PRICE * 1e-9 * 2000

        # Profit is limited by liquidity
        available_liquidity = context.get("liquidity", self.metrics.liquidity_depth) or 100000
        estimated_profit = min(available_liquidity, max_loss * 0.1)

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.INTEGER_OVERFLOW,
            max_potential_loss=max_loss,
            attack_capital_required=capital_required,
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=0,
            is_profitable=estimated_profit > gas_cost,
            profitability_margin=estimated_profit / max_loss if max_loss > 0 else 0,
            risk_score=90,  # High risk due to unlimited minting
            attack_complexity=AttackComplexity.LOW,
            time_to_execute="instant",
            detection_likelihood="low",
            mitigation_cost="$0 (use Solidity 0.8+)",
            confidence=0.8,
        )

    def _analyze_oracle_manipulation(self, context: Dict) -> EconomicImpact:
        """Analyze oracle manipulation economics."""
        return self._analyze_price_manipulation(context)  # Similar economics

    def _analyze_front_running(self, context: Dict) -> EconomicImpact:
        """Analyze front-running/MEV economics."""
        target_transaction_value = context.get("tx_value", 10000)
        slippage_tolerance = context.get("slippage", 0.01)

        max_loss = target_transaction_value * slippage_tolerance
        capital_required = target_transaction_value  # Need capital to front-run

        gas_cost = 2 * self.GAS_COSTS["swap"] * self.DEFAULT_GAS_PRICE * 1e-9 * 2000
        priority_fee = context.get("priority_fee", 50)  # Additional Gwei for priority

        estimated_profit = max_loss - gas_cost - (priority_fee * 21000 * 1e-9 * 2000)

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.FRONT_RUNNING,
            max_potential_loss=max_loss,
            attack_capital_required=capital_required,
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=0,
            is_profitable=estimated_profit > 0,
            profitability_margin=estimated_profit / max_loss if max_loss > 0 else 0,
            risk_score=40,  # Individual impact lower but aggregate significant
            attack_complexity=AttackComplexity.MEDIUM,
            time_to_execute="instant",
            detection_likelihood="high",
            mitigation_cost="$10K-$30K (commit-reveal, private mempool)",
            confidence=0.75,
        )

    def _analyze_liquidation(self, context: Dict) -> EconomicImpact:
        """Analyze liquidation attack economics."""
        position_size = context.get("position_size", 100000)
        liquidation_bonus = context.get("liquidation_bonus", 0.05)

        max_loss = position_size  # User loses position
        capital_required = position_size * 0.5  # Partial liquidation

        # Can use flash loans
        flash_loan_fees = capital_required * self.FLASH_LOAN_FEES["aave_v3"] / 10000

        gas_cost = 2 * self.GAS_COSTS["contract_call"] * self.DEFAULT_GAS_PRICE * 1e-9 * 2000
        estimated_profit = position_size * liquidation_bonus - flash_loan_fees - gas_cost

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.LIQUIDATION,
            max_potential_loss=max_loss,
            attack_capital_required=0,  # Flash loan
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=flash_loan_fees,
            is_profitable=estimated_profit > 0,
            profitability_margin=estimated_profit / max_loss if max_loss > 0 else 0,
            risk_score=min(100, int((max_loss / 100000) * 40 + 20)),
            attack_complexity=AttackComplexity.MEDIUM,
            time_to_execute="instant",
            detection_likelihood="medium",
            mitigation_cost="$5K-$20K (grace periods, better health checks)",
            confidence=0.7,
        )

    def _analyze_vault_inflation(self, context: Dict) -> EconomicImpact:
        """Analyze vault share inflation attack economics."""
        vault_tvl = context.get("vault_tvl", 100000)

        # First depositor attack
        capital_required = context.get("donation_amount", 1000)

        # Can steal subsequent deposits
        max_loss = vault_tvl - capital_required

        gas_cost = 3 * self.GAS_COSTS["contract_call"] * self.DEFAULT_GAS_PRICE * 1e-9 * 2000
        estimated_profit = max_loss - gas_cost

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.VAULT_INFLATION,
            max_potential_loss=max_loss,
            attack_capital_required=capital_required,
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=0,
            is_profitable=estimated_profit > capital_required,
            profitability_margin=estimated_profit / capital_required if capital_required > 0 else 0,
            risk_score=min(100, int((max_loss / 100000) * 60 + 20)),
            attack_complexity=AttackComplexity.LOW,
            time_to_execute="minutes",  # Need to wait for victim deposits
            detection_likelihood="medium",
            mitigation_cost="$2K-$10K (virtual offset, minimum deposit)",
            confidence=0.85,
        )

    def _analyze_bridge(self, context: Dict) -> EconomicImpact:
        """Analyze bridge attack economics."""
        bridge_tvl = context.get("bridge_tvl", self.metrics.total_value_locked) or 10000000

        # Bridge attacks can drain entire bridge
        max_loss = bridge_tvl

        capital_required = context.get("attack_capital", 0)
        gas_cost = 5 * self.GAS_COSTS["contract_call"] * self.DEFAULT_GAS_PRICE * 1e-9 * 2000

        estimated_profit = max_loss - capital_required - gas_cost

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.BRIDGE,
            max_potential_loss=max_loss,
            attack_capital_required=capital_required,
            estimated_profit=estimated_profit,
            gas_cost_estimate=gas_cost,
            flash_loan_fees=0,
            is_profitable=True,
            profitability_margin=0.99,
            risk_score=100,  # Maximum risk
            attack_complexity=AttackComplexity.HIGH,
            time_to_execute="hours",
            detection_likelihood="low",
            mitigation_cost="$50K-$200K (multi-sig, fraud proofs)",
            confidence=0.6,
        )

    def _analyze_generic(self, context: Dict) -> EconomicImpact:
        """Analyze generic vulnerability economics."""
        estimated_impact = context.get("estimated_impact", 10000)

        return EconomicImpact(
            vulnerability_type=VulnerabilityType.ACCESS_CONTROL,  # Default
            max_potential_loss=estimated_impact,
            attack_capital_required=100,
            estimated_profit=estimated_impact * 0.5,
            gas_cost_estimate=50,
            flash_loan_fees=0,
            is_profitable=True,
            profitability_margin=0.5,
            risk_score=50,
            attack_complexity=AttackComplexity.MEDIUM,
            time_to_execute="varies",
            detection_likelihood="medium",
            mitigation_cost="$5K-$20K",
            confidence=0.5,
        )

    def generate_attack_scenarios(self, vuln_type: VulnerabilityType, context: Optional[Dict] = None) -> List[AttackScenario]:
        """Generate possible attack scenarios for a vulnerability.

        Args:
            vuln_type: Type of vulnerability
            context: Additional context

        Returns:
            List of possible attack scenarios
        """
        context = context or {}
        impact = self.analyze_vulnerability(vuln_type, context)

        scenarios = []

        if vuln_type == VulnerabilityType.FLASH_LOAN:
            scenarios.append(
                AttackScenario(
                    name="Flash Loan Oracle Manipulation",
                    description="Use flash loan to manipulate oracle price and profit from mispricing",
                    steps=[
                        "1. Take flash loan from Aave/dYdX",
                        "2. Swap large amount to move DEX spot price",
                        "3. Execute victim operation at manipulated price",
                        "4. Swap back to restore price",
                        "5. Repay flash loan with profit",
                    ],
                    required_capital=0,
                    expected_profit=impact.estimated_profit,
                    success_probability=0.7,
                    prerequisites=["DEX spot price oracle", "No TWAP protection", "Sufficient flash loan liquidity"],
                    detection_risk="high",
                )
            )

        elif vuln_type == VulnerabilityType.REENTRANCY:
            scenarios.append(
                AttackScenario(
                    name="Classic Reentrancy Drain",
                    description="Exploit reentrancy to drain contract funds",
                    steps=[
                        "1. Deploy malicious contract with fallback",
                        "2. Call vulnerable withdraw function",
                        "3. In fallback, re-call withdraw before state update",
                        "4. Repeat until contract drained",
                        "5. Extract profits",
                    ],
                    required_capital=100,
                    expected_profit=impact.estimated_profit,
                    success_probability=0.9,
                    prerequisites=["No ReentrancyGuard", "External call before state update"],
                    detection_risk="medium",
                )
            )

        elif vuln_type == VulnerabilityType.GOVERNANCE:
            scenarios.append(
                AttackScenario(
                    name="Flash Loan Governance Attack",
                    description="Borrow tokens via flash loan to pass malicious proposal",
                    steps=[
                        "1. Take flash loan of governance tokens",
                        "2. Delegate voting power to attack contract",
                        "3. Vote on or execute malicious proposal",
                        "4. Return tokens",
                        "5. Proposal executes after timelock (if any)",
                    ],
                    required_capital=0,
                    expected_profit=impact.estimated_profit,
                    success_probability=0.5,
                    prerequisites=["No snapshot voting", "Tokens available in lending pools"],
                    detection_risk="medium",
                )
            )

        return scenarios

    def calculate_risk_score(self, impacts: List[EconomicImpact]) -> Dict:
        """Calculate aggregate risk score from multiple impacts.

        Args:
            impacts: List of economic impacts

        Returns:
            Aggregate risk assessment
        """
        if not impacts:
            return {"overall_score": 0, "risk_level": RiskLevel.INFORMATIONAL}

        # Weight scores by profitability and max loss
        weighted_scores = []
        for impact in impacts:
            weight = 1.0
            if impact.is_profitable:
                weight *= 1.5
            if impact.max_potential_loss > 1000000:
                weight *= 1.5
            weighted_scores.append(impact.risk_score * weight)

        avg_score = sum(weighted_scores) / len(weighted_scores)
        max_score = max(i.risk_score for i in impacts)

        # Final score is between average and max
        overall_score = int(avg_score * 0.3 + max_score * 0.7)

        if overall_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif overall_score >= 60:
            risk_level = RiskLevel.HIGH
        elif overall_score >= 40:
            risk_level = RiskLevel.MEDIUM
        elif overall_score >= 20:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.INFORMATIONAL

        return {
            "overall_score": overall_score,
            "risk_level": risk_level,
            "total_max_loss": sum(i.max_potential_loss for i in impacts),
            "total_expected_profit": sum(i.estimated_profit for i in impacts if i.is_profitable),
            "profitable_attacks": sum(1 for i in impacts if i.is_profitable),
            "trivial_exploits": sum(1 for i in impacts if i.attack_complexity == AttackComplexity.TRIVIAL),
        }
