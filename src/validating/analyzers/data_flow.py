"""Data Flow Analyzer for Vulnerability Validation.

This module provides advanced data flow analysis capabilities for tracking
taint sources, identifying critical sinks, and finding exploitable paths.
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


class SourceType(Enum):
    """Types of taint sources."""

    USER_INPUT = "user_input"  # Function parameters from external calls
    EXTERNAL_CALL = "external_call"  # Data from external contract calls
    STORAGE_READ = "storage_read"  # Data read from storage
    ORACLE_DATA = "oracle_data"  # Price/data from oracles
    MSG_DATA = "msg_data"  # msg.sender, msg.value, msg.data
    BLOCK_DATA = "block_data"  # block.timestamp, block.number
    CALLBACK_DATA = "callback_data"  # Data from callbacks


class SinkType(Enum):
    """Types of critical sinks."""

    TRANSFER = "transfer"  # Token/ETH transfers
    DELEGATE_CALL = "delegatecall"  # Delegatecall operations
    SELF_DESTRUCT = "selfdestruct"  # Contract destruction
    STATE_CHANGE = "state_change"  # State variable modifications
    EXTERNAL_CALL = "external_call"  # External contract calls
    EMIT = "emit"  # Event emissions with sensitive data
    ASSEMBLY = "assembly"  # Inline assembly operations


@dataclass
class TaintSource:
    """A source of tainted data."""

    source_type: SourceType
    name: str
    line_number: int
    code_snippet: str
    is_sanitized: bool = False
    sanitization_method: Optional[str] = None


@dataclass
class CriticalSink:
    """A critical operation that could be exploited."""

    sink_type: SinkType
    name: str
    line_number: int
    code_snippet: str
    required_privilege: Optional[str] = None


@dataclass
class DataFlowEdge:
    """An edge in the data flow graph."""

    source: str
    target: str
    edge_type: str  # assignment, parameter, return, etc.
    line_number: int


@dataclass
class DataFlowPath:
    """A path from source to sink."""

    source: TaintSource
    sink: CriticalSink
    edges: List[DataFlowEdge]
    intermediate_variables: List[str]
    is_exploitable: bool
    exploitability_reason: str
    sanitization_points: List[str]


@dataclass
class FlowNode:
    """A node in the data flow graph."""

    name: str
    node_type: str  # variable, parameter, return, call
    line_number: int
    tainted: bool = False
    taint_source: Optional[TaintSource] = None
    outgoing_edges: List[str] = field(default_factory=list)
    incoming_edges: List[str] = field(default_factory=list)


class DataFlowAnalyzer:
    """Analyze data flow for vulnerability validation.

    Features:
    - Track taint sources (user inputs, external calls, storage reads)
    - Identify critical sinks (transfers, delegatecall, selfdestruct, state changes)
    - Build data flow graphs
    - Find critical paths from sources to sinks
    - Analyze path exploitability
    - DFS-based path finding
    """

    # Taint source patterns
    SOURCE_PATTERNS = {
        SourceType.USER_INPUT: [
            r"function\s+\w+\s*\([^)]*\)",  # Function parameters
            r"calldata\s+\w+",
            r"memory\s+\w+",
        ],
        SourceType.EXTERNAL_CALL: [
            r"\.call\s*\{",
            r"\.staticcall\s*\(",
            r"\.delegatecall\s*\(",
            r"Address\.functionCall",
        ],
        SourceType.STORAGE_READ: [
            r"\b\w+\s*=\s*\w+\[\w+\]",  # Mapping reads
            r"SLOAD",
        ],
        SourceType.ORACLE_DATA: [
            r"latestRoundData\s*\(",
            r"getPrice\s*\(",
            r"getReserves\s*\(",
            r"observe\s*\(",
        ],
        SourceType.MSG_DATA: [
            r"msg\.sender",
            r"msg\.value",
            r"msg\.data",
            r"msg\.sig",
        ],
        SourceType.BLOCK_DATA: [
            r"block\.timestamp",
            r"block\.number",
            r"blockhash\s*\(",
        ],
        SourceType.CALLBACK_DATA: [
            r"executeOperation\s*\(",
            r"uniswapV\d+Call\s*\(",
            r"onFlashLoan\s*\(",
            r"receiveFlashLoan\s*\(",
        ],
    }

    # Critical sink patterns
    SINK_PATTERNS = {
        SinkType.TRANSFER: [
            r"\.transfer\s*\(",
            r"\.send\s*\(",
            r"safeTransfer\s*\(",
            r"safeTransferFrom\s*\(",
        ],
        SinkType.DELEGATE_CALL: [
            r"\.delegatecall\s*\(",
            r"DELEGATECALL",
        ],
        SinkType.SELF_DESTRUCT: [
            r"selfdestruct\s*\(",
            r"suicide\s*\(",
            r"SELFDESTRUCT",
        ],
        SinkType.STATE_CHANGE: [
            r"\w+\s*=\s*[^;]+;",  # State assignments
            r"SSTORE",
        ],
        SinkType.EXTERNAL_CALL: [
            r"\.call\s*\{",
            r"\.call\s*\(",
            r"Address\.functionCall",
        ],
        SinkType.ASSEMBLY: [
            r"assembly\s*\{",
            r"mstore\s*\(",
            r"mload\s*\(",
        ],
    }

    # Sanitization patterns
    SANITIZATION_PATTERNS = [
        r"require\s*\(",
        r"assert\s*\(",
        r"if\s*\(",
        r"modifier\s+\w+",
        r"onlyOwner",
        r"onlyAdmin",
        r"whenNotPaused",
    ]

    def __init__(self) -> None:
        """Initialize the data flow analyzer."""
        self.sources: List[TaintSource] = []
        self.sinks: List[CriticalSink] = []
        self.flow_graph: Dict[str, FlowNode] = {}
        self.edges: List[DataFlowEdge] = []
        self.paths: List[DataFlowPath] = []

    def analyze(self, code: str) -> List[DataFlowPath]:
        """Perform complete data flow analysis.

        Args:
            code: Source code to analyze

        Returns:
            List of critical data flow paths
        """
        self._reset()

        # Step 1: Identify taint sources
        self._find_sources(code)

        # Step 2: Identify critical sinks
        self._find_sinks(code)

        # Step 3: Build data flow graph
        self._build_flow_graph(code)

        # Step 4: Find paths from sources to sinks
        self._find_critical_paths()

        # Step 5: Analyze exploitability
        self._analyze_exploitability(code)

        return self.paths

    def _reset(self) -> None:
        """Reset analyzer state."""
        self.sources = []
        self.sinks = []
        self.flow_graph = {}
        self.edges = []
        self.paths = []

    def _find_sources(self, code: str) -> None:
        """Find all taint sources in code."""
        lines = code.split("\n")

        for source_type, patterns in self.SOURCE_PATTERNS.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, code, re.MULTILINE):
                        line_num = code[: match.start()].count("\n") + 1
                        start_line = max(0, line_num - 1)
                        end_line = min(len(lines), line_num + 1)
                        snippet = "\n".join(lines[start_line:end_line])

                        # Check if sanitized
                        is_sanitized, method = self._check_sanitization(code, match.start())

                        source = TaintSource(
                            source_type=source_type,
                            name=match.group(0),
                            line_number=line_num,
                            code_snippet=snippet,
                            is_sanitized=is_sanitized,
                            sanitization_method=method,
                        )
                        self.sources.append(source)
                except re.error:
                    continue

    def _find_sinks(self, code: str) -> None:
        """Find all critical sinks in code."""
        lines = code.split("\n")

        for sink_type, patterns in self.SINK_PATTERNS.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, code, re.MULTILINE):
                        line_num = code[: match.start()].count("\n") + 1
                        start_line = max(0, line_num - 1)
                        end_line = min(len(lines), line_num + 1)
                        snippet = "\n".join(lines[start_line:end_line])

                        # Check for privilege requirements
                        privilege = self._check_privilege_requirement(code, match.start())

                        sink = CriticalSink(
                            sink_type=sink_type,
                            name=match.group(0),
                            line_number=line_num,
                            code_snippet=snippet,
                            required_privilege=privilege,
                        )
                        self.sinks.append(sink)
                except re.error:
                    continue

    def _check_sanitization(self, code: str, position: int) -> Tuple[bool, Optional[str]]:
        """Check if a source is sanitized near its usage.

        Args:
            code: Full source code
            position: Position of the source

        Returns:
            Tuple of (is_sanitized, sanitization_method)
        """
        # Check 500 characters around the source
        context_start = max(0, position - 200)
        context_end = min(len(code), position + 300)
        context = code[context_start:context_end]

        for pattern in self.SANITIZATION_PATTERNS:
            try:
                match = re.search(pattern, context)
                if match:
                    return True, match.group(0)
            except re.error:
                continue

        return False, None

    def _check_privilege_requirement(self, code: str, position: int) -> Optional[str]:
        """Check if a sink requires special privileges.

        Args:
            code: Full source code
            position: Position of the sink

        Returns:
            Required privilege or None
        """
        # Find the function containing this sink
        func_start = code.rfind("function", 0, position)
        if func_start == -1:
            return None

        func_context = code[func_start:position]

        privilege_patterns = [
            r"onlyOwner",
            r"onlyAdmin",
            r"onlyRole\s*\(\s*(\w+)\s*\)",
            r"requiresAuth",
            r"auth",
        ]

        for pattern in privilege_patterns:
            try:
                match = re.search(pattern, func_context)
                if match:
                    return match.group(0)
            except re.error:
                continue

        return None

    def _build_flow_graph(self, code: str) -> None:
        """Build a data flow graph from the code.

        This is a simplified flow graph based on variable assignments
        and function calls.
        """
        # Extract variable assignments
        assignment_pattern = r"(\w+)\s*=\s*([^;]+);"

        for match in re.finditer(assignment_pattern, code, re.MULTILINE):
            target_var = match.group(1)
            source_expr = match.group(2)
            line_num = code[: match.start()].count("\n") + 1

            # Create or get target node
            if target_var not in self.flow_graph:
                self.flow_graph[target_var] = FlowNode(name=target_var, node_type="variable", line_number=line_num)

            # Find variables referenced in source expression
            source_vars = re.findall(r"\b([a-zA-Z_]\w*)\b", source_expr)

            for source_var in source_vars:
                if source_var in self.flow_graph:
                    # Create edge
                    edge = DataFlowEdge(source=source_var, target=target_var, edge_type="assignment", line_number=line_num)
                    self.edges.append(edge)

                    # Update node connections
                    self.flow_graph[source_var].outgoing_edges.append(target_var)
                    self.flow_graph[target_var].incoming_edges.append(source_var)

    def _find_critical_paths(self) -> None:
        """Find paths from sources to sinks using DFS."""
        for source in self.sources:
            for sink in self.sinks:
                # Try to find a path from source to sink
                path_edges = self._dfs_find_path(source, sink)

                if path_edges:
                    path = DataFlowPath(
                        source=source,
                        sink=sink,
                        edges=path_edges,
                        intermediate_variables=[e.target for e in path_edges[:-1]],
                        is_exploitable=False,  # Will be determined later
                        exploitability_reason="",
                        sanitization_points=[],
                    )
                    self.paths.append(path)

    def _dfs_find_path(self, source: TaintSource, sink: CriticalSink, max_depth: int = 20) -> List[DataFlowEdge]:
        """Find a path from source to sink using DFS.

        Args:
            source: The taint source
            sink: The critical sink
            max_depth: Maximum search depth

        Returns:
            List of edges forming the path, or empty list if no path found
        """
        # Extract variable names from source and sink
        source_vars = re.findall(r"\b([a-zA-Z_]\w*)\b", source.name)
        sink_vars = re.findall(r"\b([a-zA-Z_]\w*)\b", sink.name)

        if not source_vars or not sink_vars:
            return []

        # DFS from source variables to sink variables
        for source_var in source_vars:
            for sink_var in sink_vars:
                visited: Set[str] = set()
                path = self._dfs_helper(source_var, sink_var, visited, [], max_depth)
                if path:
                    return path

        return []

    def _dfs_helper(self, current: str, target: str, visited: Set[str], path: List[DataFlowEdge], max_depth: int) -> List[DataFlowEdge]:
        """DFS helper function.

        Args:
            current: Current node
            target: Target node
            visited: Set of visited nodes
            path: Current path
            max_depth: Maximum remaining depth

        Returns:
            Path to target or empty list
        """
        if max_depth <= 0:
            return []

        if current == target:
            return path

        if current in visited:
            return []

        visited.add(current)

        # Find edges from current node
        for edge in self.edges:
            if edge.source == current:
                new_path = path + [edge]
                result = self._dfs_helper(edge.target, target, visited.copy(), new_path, max_depth - 1)
                if result:
                    return result

        return []

    def _analyze_exploitability(self, code: str) -> None:
        """Analyze exploitability of each path."""
        for path in self.paths:
            # Check if source is sanitized
            if path.source.is_sanitized:
                path.is_exploitable = False
                path.exploitability_reason = f"Source is sanitized by {path.source.sanitization_method}"
                path.sanitization_points.append(path.source.sanitization_method or "unknown")
                continue

            # Check if sink requires privilege
            if path.sink.required_privilege:
                path.is_exploitable = False
                path.exploitability_reason = f"Sink requires privilege: {path.sink.required_privilege}"
                continue

            # Check for sanitization along the path
            has_sanitization = False
            for var in path.intermediate_variables:
                # Check if there's a require/assert on this variable
                context_pattern = rf"require\s*\([^)]*{re.escape(var)}[^)]*\)"
                if re.search(context_pattern, code):
                    has_sanitization = True
                    path.sanitization_points.append(f"require on {var}")

            if has_sanitization:
                path.is_exploitable = False
                path.exploitability_reason = "Path has validation checks"
            else:
                path.is_exploitable = True
                path.exploitability_reason = "Untrusted data flows to critical operation without validation"

    def get_exploitable_paths(self) -> List[DataFlowPath]:
        """Get only exploitable paths.

        Returns:
            List of exploitable data flow paths
        """
        return [p for p in self.paths if p.is_exploitable]

    def get_summary(self) -> Dict:
        """Get analysis summary.

        Returns:
            Dictionary with analysis statistics
        """
        return {
            "total_sources": len(self.sources),
            "total_sinks": len(self.sinks),
            "total_paths": len(self.paths),
            "exploitable_paths": len(self.get_exploitable_paths()),
            "source_types": {st.value: len([s for s in self.sources if s.source_type == st]) for st in SourceType},
            "sink_types": {st.value: len([s for s in self.sinks if s.sink_type == st]) for st in SinkType},
        }


class TaintAnalyzer:
    """Taint analysis to track user-controlled data through programs.

    Features:
    - Find tainted paths (user input → critical operation)
    - Identify untainted sinks (potentially safe)
    - Check if specific variables are tainted
    """

    def __init__(self, data_flow_analyzer: Optional[DataFlowAnalyzer] = None) -> None:
        """Initialize the taint analyzer.

        Args:
            data_flow_analyzer: Optional pre-configured data flow analyzer
        """
        self.dfa = data_flow_analyzer or DataFlowAnalyzer()
        self.tainted_vars: Set[str] = set()

    def analyze(self, code: str) -> Dict:
        """Perform taint analysis on code.

        Args:
            code: Source code to analyze

        Returns:
            Dictionary with taint analysis results
        """
        # Run data flow analysis first
        paths = self.dfa.analyze(code)

        # Mark tainted variables
        self._propagate_taint()

        # Find tainted sinks
        tainted_sinks = self._find_tainted_sinks()

        # Find untainted sinks
        untainted_sinks = self._find_untainted_sinks()

        return {
            "tainted_variables": list(self.tainted_vars),
            "tainted_paths": [p for p in paths if p.is_exploitable],
            "tainted_sinks": tainted_sinks,
            "untainted_sinks": untainted_sinks,
            "total_sinks": len(self.dfa.sinks),
        }

    def _propagate_taint(self) -> None:
        """Propagate taint from sources through the flow graph."""
        # Initialize with source variables
        for source in self.dfa.sources:
            vars_in_source = re.findall(r"\b([a-zA-Z_]\w*)\b", source.name)
            for var in vars_in_source:
                if var in self.dfa.flow_graph:
                    self.dfa.flow_graph[var].tainted = True
                    self.dfa.flow_graph[var].taint_source = source
                    self.tainted_vars.add(var)

        # Propagate taint through edges
        changed = True
        while changed:
            changed = False
            for edge in self.dfa.edges:
                if edge.source in self.tainted_vars and edge.target not in self.tainted_vars:
                    self.tainted_vars.add(edge.target)
                    if edge.target in self.dfa.flow_graph:
                        source_node = self.dfa.flow_graph.get(edge.source)
                        self.dfa.flow_graph[edge.target].tainted = True
                        if source_node:
                            self.dfa.flow_graph[edge.target].taint_source = source_node.taint_source
                    changed = True

    def _find_tainted_sinks(self) -> List[CriticalSink]:
        """Find sinks that receive tainted data.

        Returns:
            List of tainted sinks
        """
        tainted_sinks = []

        for sink in self.dfa.sinks:
            # Check if any variable in sink is tainted
            sink_vars = re.findall(r"\b([a-zA-Z_]\w*)\b", sink.code_snippet)
            for var in sink_vars:
                if var in self.tainted_vars:
                    tainted_sinks.append(sink)
                    break

        return tainted_sinks

    def _find_untainted_sinks(self) -> List[CriticalSink]:
        """Find sinks that don't receive tainted data.

        Returns:
            List of untainted (potentially safe) sinks
        """
        tainted_sinks = self._find_tainted_sinks()
        return [s for s in self.dfa.sinks if s not in tainted_sinks]

    def is_variable_tainted(self, variable_name: str) -> bool:
        """Check if a specific variable is tainted.

        Args:
            variable_name: Name of the variable to check

        Returns:
            True if the variable is tainted
        """
        return variable_name in self.tainted_vars

    def get_taint_source(self, variable_name: str) -> Optional[TaintSource]:
        """Get the taint source for a variable.

        Args:
            variable_name: Name of the variable

        Returns:
            The taint source or None if not tainted
        """
        if variable_name in self.dfa.flow_graph:
            return self.dfa.flow_graph[variable_name].taint_source
        return None

    def get_taint_path(self, variable_name: str) -> List[str]:
        """Get the propagation path for a tainted variable.

        Args:
            variable_name: Name of the tainted variable

        Returns:
            List of variable names in the taint path
        """
        if variable_name not in self.tainted_vars:
            return []

        path = [variable_name]
        current = variable_name

        # Trace back through incoming edges
        while current in self.dfa.flow_graph:
            node = self.dfa.flow_graph[current]
            if node.incoming_edges:
                # Find a tainted incoming edge
                for prev in node.incoming_edges:
                    if prev in self.tainted_vars:
                        if prev not in path:  # Avoid cycles
                            path.insert(0, prev)
                            current = prev
                            break
                else:
                    break
            else:
                break

        return path
