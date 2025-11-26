"""Cross-Contract Analysis for Protocol-Level Security.

This module provides analysis capabilities for multi-contract protocols,
including dependency mapping, state flow analysis, and cross-contract vulnerabilities.
"""

import re
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple


class ContractRole(Enum):
    """Roles contracts play in a protocol."""

    CORE = "core"  # Core protocol logic
    TOKEN = "token"  # Token contracts
    GOVERNANCE = "governance"  # Governance contracts
    ORACLE = "oracle"  # Price/data oracles
    VAULT = "vault"  # Asset vaults
    ROUTER = "router"  # Router/aggregator
    PROXY = "proxy"  # Proxy contracts
    LIBRARY = "library"  # Shared libraries
    PERIPHERAL = "peripheral"  # Peripheral contracts


class DependencyType(Enum):
    """Types of contract dependencies."""

    INHERITANCE = "inheritance"
    INTERFACE = "interface"
    EXTERNAL_CALL = "external_call"
    DELEGATE_CALL = "delegatecall"
    LIBRARY_CALL = "library_call"
    CALLBACK = "callback"
    ORACLE = "oracle"
    TOKEN = "token"


class VulnerabilityImpact(Enum):
    """Impact scope of vulnerabilities."""

    LOCAL = "local"  # Single contract
    MULTI_CONTRACT = "multi_contract"  # Multiple contracts
    PROTOCOL_WIDE = "protocol_wide"  # Entire protocol
    ECOSYSTEM = "ecosystem"  # Other protocols affected


@dataclass
class ContractNode:
    """A contract in the dependency graph."""

    name: str
    file_path: str
    role: ContractRole
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    external_calls: List[str] = field(default_factory=list)
    state_variables: List[str] = field(default_factory=list)
    criticality: int = 0  # 0-100


@dataclass
class DependencyEdge:
    """An edge in the dependency graph."""

    source: str
    target: str
    dependency_type: DependencyType
    call_sites: List[int] = field(default_factory=list)  # Line numbers


@dataclass
class StateTransition:
    """A state transition in a contract."""

    variable: str
    old_value: Optional[str]
    new_value: str
    function: str
    contract: str
    line_number: int


@dataclass
class CrossContractVulnerability:
    """A vulnerability spanning multiple contracts."""

    name: str
    description: str
    affected_contracts: List[str]
    attack_path: List[str]
    impact: VulnerabilityImpact
    severity: str
    mitigation: str


@dataclass
class InvariantViolation:
    """A protocol invariant that may be violated."""

    invariant: str
    description: str
    violating_path: List[str]
    contracts_involved: List[str]
    severity: str


class DependencyMapper:
    """Map contract dependencies for protocol-level analysis.

    Features:
    - Build dependency graphs
    - Detect cyclic dependencies
    - Identify critical contracts
    - Find cross-contract vulnerabilities
    """

    # Patterns for detecting dependencies
    INHERITANCE_PATTERN = r"contract\s+(\w+)\s+is\s+([^{]+)\{"
    INTERFACE_PATTERN = r"interface\s+I(\w+)"
    IMPORT_PATTERN = r"import\s+[\"']([^\"']+)[\"']"
    EXTERNAL_CALL_PATTERN = r"(\w+)\.(\w+)\s*\("
    DELEGATECALL_PATTERN = r"\.delegatecall\s*\("
    LIBRARY_PATTERN = r"using\s+(\w+)\s+for"

    def __init__(self) -> None:
        """Initialize the dependency mapper."""
        self.contracts: Dict[str, ContractNode] = {}
        self.edges: List[DependencyEdge] = []
        self.dependency_graph: Dict[str, Set[str]] = {}

    def analyze(self, contracts: Dict[str, str]) -> Dict:
        """Analyze dependencies across contracts.

        Args:
            contracts: Dictionary mapping contract names to source code

        Returns:
            Dependency analysis results
        """
        self._reset()

        # Parse each contract
        for name, code in contracts.items():
            self._parse_contract(name, code)

        # Build dependency graph
        self._build_graph()

        # Detect cycles
        cycles = self._detect_cycles()

        # Calculate criticality
        self._calculate_criticality()

        # Find critical paths
        critical_paths = self._find_critical_paths()

        return {
            "contracts": len(self.contracts),
            "edges": len(self.edges),
            "cycles": cycles,
            "critical_contracts": self._get_critical_contracts(),
            "critical_paths": critical_paths,
        }

    def _reset(self) -> None:
        """Reset mapper state."""
        self.contracts = {}
        self.edges = []
        self.dependency_graph = {}

    def _parse_contract(self, name: str, code: str) -> None:
        """Parse a contract and extract dependencies."""
        # Determine contract role
        role = self._determine_role(name, code)

        node = ContractNode(name=name, file_path=f"{name}.sol", role=role)

        # Find inheritance
        inheritance_match = re.search(self.INHERITANCE_PATTERN, code)
        if inheritance_match:
            parents = [p.strip() for p in inheritance_match.group(2).split(",")]
            for parent in parents:
                parent_name = parent.split("(")[0].strip()
                node.dependencies.append(parent_name)
                self.edges.append(DependencyEdge(source=name, target=parent_name, dependency_type=DependencyType.INHERITANCE))

        # Find library usage
        for match in re.finditer(self.LIBRARY_PATTERN, code):
            lib_name = match.group(1)
            node.dependencies.append(lib_name)
            self.edges.append(DependencyEdge(source=name, target=lib_name, dependency_type=DependencyType.LIBRARY_CALL))

        # Find external calls
        for match in re.finditer(self.EXTERNAL_CALL_PATTERN, code):
            target = match.group(1)
            if target not in ["msg", "block", "tx", "this", "super"]:
                node.external_calls.append(target)
                line_num = code[: match.start()].count("\n") + 1
                self.edges.append(DependencyEdge(source=name, target=target, dependency_type=DependencyType.EXTERNAL_CALL, call_sites=[line_num]))

        # Find delegatecalls
        if re.search(self.DELEGATECALL_PATTERN, code):
            for match in re.finditer(r"(\w+)\.delegatecall", code):
                target = match.group(1)
                node.dependencies.append(target)
                self.edges.append(DependencyEdge(source=name, target=target, dependency_type=DependencyType.DELEGATE_CALL))

        # Extract state variables
        state_var_pattern = r"(?:mapping|uint|int|address|bool|string|bytes)\s+(?:public|private|internal)?\s*(\w+)\s*[;=]"
        for match in re.finditer(state_var_pattern, code):
            node.state_variables.append(match.group(1))

        self.contracts[name] = node

    def _determine_role(self, name: str, code: str) -> ContractRole:
        """Determine the role of a contract."""
        name_lower = name.lower()

        if "governance" in name_lower or "governor" in name_lower or "voting" in name_lower:
            return ContractRole.GOVERNANCE
        elif "token" in name_lower or "erc20" in name_lower or "erc721" in name_lower:
            return ContractRole.TOKEN
        elif "oracle" in name_lower or "price" in name_lower:
            return ContractRole.ORACLE
        elif "vault" in name_lower or "pool" in name_lower:
            return ContractRole.VAULT
        elif "router" in name_lower or "aggregator" in name_lower:
            return ContractRole.ROUTER
        elif "proxy" in name_lower or "upgradeable" in name_lower:
            return ContractRole.PROXY
        elif "library" in name_lower or re.search(r"^[A-Z][a-z]+Lib$", name):
            return ContractRole.LIBRARY
        elif "ERC20" in code or "ERC721" in code:
            return ContractRole.TOKEN
        else:
            return ContractRole.CORE

    def _build_graph(self) -> None:
        """Build the dependency graph."""
        for contract in self.contracts.values():
            if contract.name not in self.dependency_graph:
                self.dependency_graph[contract.name] = set()

            for dep in contract.dependencies:
                self.dependency_graph[contract.name].add(dep)

            for ext_call in contract.external_calls:
                self.dependency_graph[contract.name].add(ext_call)

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cyclic dependencies in the graph."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.dependency_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.remove(node)

        for node in self.dependency_graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _calculate_criticality(self) -> None:
        """Calculate criticality score for each contract."""
        for name, contract in self.contracts.items():
            score = 0

            # More dependents = more critical
            dependents = [e for e in self.edges if e.target == name]
            score += len(dependents) * 10

            # Core and governance contracts are more critical
            if contract.role in [ContractRole.CORE, ContractRole.GOVERNANCE]:
                score += 30
            elif contract.role in [ContractRole.VAULT, ContractRole.TOKEN]:
                score += 20

            # More external calls = more attack surface
            score += len(contract.external_calls) * 5

            # State variables indicate more responsibility
            score += len(contract.state_variables) * 2

            contract.criticality = min(100, score)

            # Track dependents
            for edge in self.edges:
                if edge.target == name and edge.source in self.contracts:
                    contract.dependents.append(edge.source)

    def _get_critical_contracts(self) -> List[str]:
        """Get list of critical contracts sorted by criticality."""
        sorted_contracts = sorted(self.contracts.values(), key=lambda c: c.criticality, reverse=True)
        return [c.name for c in sorted_contracts[:5]]

    def _find_critical_paths(self) -> List[List[str]]:
        """Find critical execution paths through the protocol."""
        critical_paths = []

        # Find paths from peripheral contracts to core/vault contracts
        core_contracts = [c.name for c in self.contracts.values() if c.role in [ContractRole.CORE, ContractRole.VAULT]]

        for name, contract in self.contracts.items():
            if contract.role == ContractRole.PERIPHERAL:
                for core in core_contracts:
                    path = self._find_path(name, core)
                    if path and len(path) > 1:
                        critical_paths.append(path)

        return critical_paths[:10]  # Limit results

    def _find_path(self, start: str, end: str, visited: Optional[Set[str]] = None, max_depth: int = 10) -> Optional[List[str]]:
        """Find a path between two contracts."""
        if visited is None:
            visited = set()

        if max_depth <= 0:
            return None

        if start == end:
            return [start]

        visited.add(start)

        for neighbor in self.dependency_graph.get(start, set()):
            if neighbor not in visited:
                path = self._find_path(neighbor, end, visited.copy(), max_depth - 1)
                if path:
                    return [start] + path

        return None


class StateFlowAnalyzer:
    """Analyze state flow across contracts.

    Features:
    - Track state transitions
    - Identify invariant violations
    - Find critical execution paths
    """

    def __init__(self) -> None:
        """Initialize the state flow analyzer."""
        self.transitions: List[StateTransition] = []
        self.invariants: List[str] = []

    def analyze(self, contracts: Dict[str, str], dependency_mapper: Optional[DependencyMapper] = None) -> Dict:
        """Analyze state flow across contracts.

        Args:
            contracts: Dictionary mapping contract names to source code
            dependency_mapper: Optional pre-configured dependency mapper

        Returns:
            State flow analysis results
        """
        self._reset()

        mapper = dependency_mapper or DependencyMapper()
        if not dependency_mapper:
            mapper.analyze(contracts)

        # Extract state transitions from each contract
        for name, code in contracts.items():
            self._extract_transitions(name, code)

        # Identify potential invariant violations
        violations = self._check_invariants(mapper)

        # Find critical state paths
        critical_paths = self._find_critical_state_paths(mapper)

        return {"transitions": len(self.transitions), "potential_violations": violations, "critical_state_paths": critical_paths}

    def _reset(self) -> None:
        """Reset analyzer state."""
        self.transitions = []
        self.invariants = []

    def _extract_transitions(self, contract_name: str, code: str) -> None:
        """Extract state transitions from a contract."""
        # Pattern for state assignments in functions
        func_pattern = r"function\s+(\w+)[^{]+\{([^}]+)\}"

        for func_match in re.finditer(func_pattern, code, re.DOTALL):
            func_name = func_match.group(1)
            func_body = func_match.group(2)

            # Find assignments
            assign_pattern = r"(\w+)\s*=\s*([^;]+);"
            for assign_match in re.finditer(assign_pattern, func_body):
                var_name = assign_match.group(1)
                new_value = assign_match.group(2).strip()
                line_num = code[: assign_match.start()].count("\n") + 1

                transition = StateTransition(variable=var_name, old_value=None, new_value=new_value, function=func_name, contract=contract_name, line_number=line_num)
                self.transitions.append(transition)

    def _check_invariants(self, mapper: DependencyMapper) -> List[InvariantViolation]:
        """Check for potential invariant violations."""
        violations = []

        # Check for state changes without proper guards
        for transition in self.transitions:
            # Check if critical state is modified in non-critical function
            if transition.contract in mapper.contracts:
                contract = mapper.contracts[transition.contract]
                if contract.role in [ContractRole.VAULT, ContractRole.TOKEN]:
                    # Check for balance/supply modifications
                    if any(kw in transition.variable.lower() for kw in ["balance", "supply", "total"]):
                        violations.append(
                            InvariantViolation(
                                invariant=f"{transition.variable} should only change via controlled operations",
                                description=f"State variable {transition.variable} modified in {transition.function}",
                                violating_path=[f"{transition.contract}.{transition.function}"],
                                contracts_involved=[transition.contract],
                                severity="medium",
                            )
                        )

        return violations

    def _find_critical_state_paths(self, mapper: DependencyMapper) -> List[List[str]]:
        """Find critical state modification paths."""
        paths = []

        # Group transitions by variable
        var_transitions: Dict[str, List[StateTransition]] = {}
        for t in self.transitions:
            key = f"{t.contract}.{t.variable}"
            if key not in var_transitions:
                var_transitions[key] = []
            var_transitions[key].append(t)

        # Find variables modified from multiple places
        for var, trans in var_transitions.items():
            if len(trans) > 1:
                path = [f"{t.contract}.{t.function}" for t in trans]
                paths.append(path)

        return paths[:10]


class CrossContractAnalyzer:
    """Comprehensive cross-contract security analysis.

    Combines dependency mapping and state flow analysis
    to identify protocol-level vulnerabilities.
    """

    def __init__(self) -> None:
        """Initialize the cross-contract analyzer."""
        self.dependency_mapper = DependencyMapper()
        self.state_analyzer = StateFlowAnalyzer()
        self.vulnerabilities: List[CrossContractVulnerability] = []

    def analyze(self, contracts: Dict[str, str]) -> Dict:
        """Perform comprehensive cross-contract analysis.

        Args:
            contracts: Dictionary mapping contract names to source code

        Returns:
            Complete analysis results
        """
        self.vulnerabilities = []

        # Dependency analysis
        dep_results = self.dependency_mapper.analyze(contracts)

        # State flow analysis
        state_results = self.state_analyzer.analyze(contracts, self.dependency_mapper)

        # Find cross-contract vulnerabilities
        self._find_vulnerabilities(contracts)

        return {
            "dependencies": dep_results,
            "state_flow": state_results,
            "cross_contract_vulnerabilities": [
                {"name": v.name, "severity": v.severity, "affected_contracts": v.affected_contracts, "attack_path": v.attack_path} for v in self.vulnerabilities
            ],
            "overall_risk": self._calculate_overall_risk(),
        }

    def _find_vulnerabilities(self, contracts: Dict[str, str]) -> None:
        """Find cross-contract vulnerabilities."""
        # Check for reentrancy across contracts
        self._check_cross_reentrancy(contracts)

        # Check for privilege escalation paths
        self._check_privilege_escalation()

        # Check for oracle manipulation paths
        self._check_oracle_manipulation(contracts)

    def _check_cross_reentrancy(self, contracts: Dict[str, str]) -> None:
        """Check for cross-contract reentrancy."""
        for name, code in contracts.items():
            # Look for external calls followed by state changes
            external_call_pattern = r"\.call\{[^}]*\}\([^)]*\)|\.transfer\(|\.send\("

            for match in re.finditer(external_call_pattern, code):
                pos = match.end()
                # Check for state changes after external call
                remaining = code[pos : pos + 500]
                if re.search(r"\w+\s*=\s*[^;]+;", remaining):
                    self.vulnerabilities.append(
                        CrossContractVulnerability(
                            name="Cross-Contract Reentrancy",
                            description="External call made before state update could allow reentrancy",
                            affected_contracts=[name],
                            attack_path=[f"{name} -> external -> {name}"],
                            impact=VulnerabilityImpact.MULTI_CONTRACT,
                            severity="high",
                            mitigation="Apply ReentrancyGuard; follow checks-effects-interactions",
                        )
                    )

    def _check_privilege_escalation(self) -> None:
        """Check for privilege escalation paths."""
        # Find paths from peripheral to admin functions
        for name, contract in self.dependency_mapper.contracts.items():
            if contract.role == ContractRole.PERIPHERAL:
                for dep in contract.dependencies:
                    if dep in self.dependency_mapper.contracts:
                        dep_contract = self.dependency_mapper.contracts[dep]
                        if dep_contract.role == ContractRole.GOVERNANCE:
                            self.vulnerabilities.append(
                                CrossContractVulnerability(
                                    name="Privilege Escalation Path",
                                    description=f"Peripheral contract {name} has path to governance",
                                    affected_contracts=[name, dep],
                                    attack_path=[name, dep],
                                    impact=VulnerabilityImpact.PROTOCOL_WIDE,
                                    severity="medium",
                                    mitigation="Add additional access controls on governance operations",
                                )
                            )

    def _check_oracle_manipulation(self, contracts: Dict[str, str]) -> None:
        """Check for oracle manipulation vectors."""
        oracle_contracts = [name for name, c in self.dependency_mapper.contracts.items() if c.role == ContractRole.ORACLE]

        for oracle in oracle_contracts:
            # Find contracts that depend on this oracle
            dependents = [e.source for e in self.dependency_mapper.edges if e.target == oracle]

            if len(dependents) > 1:
                # Multiple contracts depend on same oracle - manipulation could affect all
                self.vulnerabilities.append(
                    CrossContractVulnerability(
                        name="Shared Oracle Manipulation Risk",
                        description=f"Multiple contracts depend on oracle {oracle}",
                        affected_contracts=[oracle] + dependents,
                        attack_path=[oracle] + dependents,
                        impact=VulnerabilityImpact.PROTOCOL_WIDE,
                        severity="medium",
                        mitigation="Use multiple oracle sources; implement price deviation checks",
                    )
                )

    def _calculate_overall_risk(self) -> str:
        """Calculate overall protocol risk level."""
        if not self.vulnerabilities:
            return "low"

        high_count = sum(1 for v in self.vulnerabilities if v.severity == "high")
        medium_count = sum(1 for v in self.vulnerabilities if v.severity == "medium")

        if high_count >= 2:
            return "critical"
        elif high_count >= 1 or medium_count >= 3:
            return "high"
        elif medium_count >= 1:
            return "medium"
        else:
            return "low"

    def get_attack_surface(self) -> Dict:
        """Get protocol attack surface analysis."""
        entry_points = []
        critical_assets = []

        for name, contract in self.dependency_mapper.contracts.items():
            if contract.role in [ContractRole.ROUTER, ContractRole.PERIPHERAL]:
                entry_points.append(name)
            if contract.role in [ContractRole.VAULT, ContractRole.TOKEN]:
                critical_assets.append(name)

        return {
            "entry_points": entry_points,
            "critical_assets": critical_assets,
            "external_dependencies": len([e for e in self.dependency_mapper.edges if e.dependency_type == DependencyType.EXTERNAL_CALL]),
            "delegate_calls": len([e for e in self.dependency_mapper.edges if e.dependency_type == DependencyType.DELEGATE_CALL]),
        }


class MitigationVerificationEngine:
    """Verify if mitigations are effective."""

    COMMON_MITIGATIONS = {
        "reentrancy": ["ReentrancyGuard", "nonReentrant", "mutex", "_status"],
        "access_control": ["onlyOwner", "onlyAdmin", "onlyRole", "auth", "requiresAuth"],
        "pausable": ["whenNotPaused", "paused", "Pausable"],
        "oracle": ["TWAP", "observe", "minDelay", "deviation"],
    }

    def verify_mitigation(self, code: str, vulnerability_type: str) -> Dict:
        """Verify if mitigation is present for a vulnerability type.

        Args:
            code: Source code to check
            vulnerability_type: Type of vulnerability

        Returns:
            Mitigation verification results
        """
        mitigations_found = []
        coverage = 0.0

        if vulnerability_type in self.COMMON_MITIGATIONS:
            checks = self.COMMON_MITIGATIONS[vulnerability_type]
            found = 0

            for check in checks:
                if check in code:
                    mitigations_found.append(check)
                    found += 1

            coverage = found / len(checks) if checks else 0

        return {"mitigations_found": mitigations_found, "coverage": coverage, "residual_risk": "low" if coverage > 0.5 else "high", "recommendations": self._get_recommendations(vulnerability_type, mitigations_found)}

    def _get_recommendations(self, vuln_type: str, found_mitigations: List[str]) -> List[str]:
        """Get recommendations based on missing mitigations."""
        recommendations = []

        if vuln_type == "reentrancy" and "ReentrancyGuard" not in found_mitigations:
            recommendations.append("Add OpenZeppelin ReentrancyGuard to sensitive functions")

        if vuln_type == "access_control" and not any(m in found_mitigations for m in ["onlyOwner", "onlyRole"]):
            recommendations.append("Implement role-based access control using OpenZeppelin AccessControl")

        if vuln_type == "oracle" and "TWAP" not in found_mitigations:
            recommendations.append("Use TWAP oracle with minimum 30-minute window instead of spot prices")

        return recommendations


class EconomicAttackVectorAnalyzer:
    """Analyze economic attack vectors in DeFi protocols."""

    def __init__(self) -> None:
        """Initialize the economic attack vector analyzer."""
        self.attack_vectors: List[Dict] = []

    def analyze(self, contracts: Dict[str, str], tvl: float = 0) -> Dict:
        """Analyze economic attack vectors.

        Args:
            contracts: Contract source code
            tvl: Total value locked in USD

        Returns:
            Attack vector analysis
        """
        self.attack_vectors = []

        # Flash loan attack paths
        self._analyze_flash_loan_paths(contracts, tvl)

        # Oracle manipulation vectors
        self._analyze_oracle_vectors(contracts, tvl)

        # Governance attack feasibility
        self._analyze_governance_vectors(contracts, tvl)

        return {"attack_vectors": self.attack_vectors, "highest_risk_vector": max(self.attack_vectors, key=lambda x: x.get("risk_score", 0)) if self.attack_vectors else None, "total_at_risk": sum(v.get("potential_loss", 0) for v in self.attack_vectors)}

    def _analyze_flash_loan_paths(self, contracts: Dict[str, str], tvl: float) -> None:
        """Analyze flash loan attack paths."""
        for name, code in contracts.items():
            if any(pattern in code for pattern in ["flashLoan", "executeOperation", "onFlashLoan"]):
                self.attack_vectors.append(
                    {"type": "flash_loan", "contract": name, "potential_loss": tvl * 0.5, "capital_required": 0, "risk_score": 80, "complexity": "medium"}
                )

    def _analyze_oracle_vectors(self, contracts: Dict[str, str], tvl: float) -> None:
        """Analyze oracle manipulation vectors."""
        for name, code in contracts.items():
            if any(pattern in code for pattern in ["getReserves", "slot0", "get_dy"]):
                self.attack_vectors.append(
                    {"type": "oracle_manipulation", "contract": name, "potential_loss": tvl * 0.3, "capital_required": tvl * 0.1, "risk_score": 70, "complexity": "medium"}
                )

    def _analyze_governance_vectors(self, contracts: Dict[str, str], tvl: float) -> None:
        """Analyze governance attack vectors."""
        for name, code in contracts.items():
            if any(pattern in code for pattern in ["propose", "castVote", "execute"]):
                # Check for timelock
                has_timelock = "timelock" in code.lower() or "delay" in code.lower()
                risk = 50 if has_timelock else 75

                self.attack_vectors.append({"type": "governance", "contract": name, "potential_loss": tvl, "capital_required": 0, "risk_score": risk, "complexity": "high" if has_timelock else "medium"})
