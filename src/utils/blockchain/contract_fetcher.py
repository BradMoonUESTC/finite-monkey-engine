"""Multi-Chain Contract Fetcher.

This module provides functionality to fetch verified contract source code
from block explorers across multiple blockchain networks.
"""

import json
import os
import re
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from .chain_config import ChainConfig
from .chain_config import get_chain_by_name
from .chain_config import SUPPORTED_CHAINS


class ProxyType(Enum):
    """Types of proxy contracts."""

    NONE = "none"
    EIP_1967 = "eip1967"  # Standard transparent proxy
    UUPS = "uups"  # Universal Upgradeable Proxy Standard
    TRANSPARENT = "transparent"  # OpenZeppelin TransparentProxy
    BEACON = "beacon"  # Beacon proxy
    DIAMOND = "diamond"  # EIP-2535 Diamond
    GNOSIS_SAFE = "gnosis_safe"  # Gnosis Safe proxy
    MINIMAL = "minimal"  # EIP-1167 minimal proxy


@dataclass
class ContractSource:
    """Source code for a contract."""

    name: str
    content: str
    file_path: str


@dataclass
class ContractMetadata:
    """Metadata for a fetched contract."""

    address: str
    chain: str
    name: str
    compiler_version: str
    optimization_enabled: bool
    optimization_runs: int
    evm_version: str
    license: str
    proxy_type: ProxyType
    implementation_address: Optional[str]
    abi: List[Dict]
    sources: List[ContractSource] = field(default_factory=list)


@dataclass
class FetchResult:
    """Result of a contract fetch operation."""

    success: bool
    metadata: Optional[ContractMetadata]
    error: Optional[str]
    raw_response: Optional[Dict] = None


class ContractFetcher:
    """Fetch verified contract source code from block explorers.

    Features:
    - Etherscan v2 API integration
    - Multi-chain support (75+ chains)
    - Proxy contract detection (EIP-1967, UUPS, Transparent, Beacon)
    - Implementation address resolution
    - Source code flattening
    """

    # Storage slots for proxy detection
    PROXY_SLOTS = {
        # EIP-1967 implementation slot
        "implementation": "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
        # EIP-1967 admin slot
        "admin": "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",
        # EIP-1967 beacon slot
        "beacon": "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50",
        # OpenZeppelin implementation slot (older)
        "oz_implementation": "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",
    }

    # Proxy signature patterns
    PROXY_PATTERNS = {
        ProxyType.UUPS: [
            r"function\s+upgradeTo\s*\(",
            r"function\s+upgradeToAndCall\s*\(",
            r"_authorizeUpgrade\s*\(",
        ],
        ProxyType.TRANSPARENT: [
            r"TransparentUpgradeableProxy",
            r"ProxyAdmin",
            r"_setAdmin\s*\(",
        ],
        ProxyType.BEACON: [
            r"BeaconProxy",
            r"UpgradeableBeacon",
            r"IBeacon",
        ],
        ProxyType.DIAMOND: [
            r"diamondCut",
            r"IDiamond",
            r"DiamondStorage",
        ],
        ProxyType.MINIMAL: [
            r"clone\s*\(",
            r"create2\s*\(",
            r"EIP1167",
        ],
        ProxyType.GNOSIS_SAFE: [
            r"GnosisSafe",
            r"SafeProxy",
        ],
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the contract fetcher.

        Args:
            api_key: Etherscan API key (uses ETHERSCAN_API_KEY env var if not provided)
        """
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY", "")
        self._http_client: Optional[Any] = None

    def _get_http_client(self) -> Any:
        """Get or create HTTP client."""
        if self._http_client is None:
            try:
                import httpx

                self._http_client = httpx.Client(timeout=30.0)
            except ImportError:
                raise ImportError("httpx package is required for contract fetching")
        return self._http_client

    def fetch(self, address: str, chain: str = "ethereum") -> FetchResult:
        """Fetch contract source code from a block explorer.

        Args:
            address: Contract address
            chain: Chain name (default: ethereum)

        Returns:
            FetchResult with contract metadata and sources
        """
        # Get chain config
        chain_config = get_chain_by_name(chain)
        if not chain_config:
            return FetchResult(success=False, metadata=None, error=f"Unsupported chain: {chain}")

        if not chain_config.explorer_api_url:
            return FetchResult(success=False, metadata=None, error=f"No explorer API for chain: {chain}")

        # Fetch contract source
        try:
            source_result = self._fetch_source(address, chain_config)
            if not source_result["success"]:
                return FetchResult(success=False, metadata=None, error=source_result.get("error", "Unknown error"), raw_response=source_result.get("raw"))

            # Check if it's a proxy
            proxy_type, impl_address = self._detect_proxy(address, chain_config, source_result.get("source", ""))

            # If proxy, also fetch implementation
            impl_sources: List[ContractSource] = []
            if impl_address and proxy_type != ProxyType.NONE:
                impl_result = self._fetch_source(impl_address, chain_config)
                if impl_result["success"]:
                    impl_sources = self._parse_sources(impl_result)

            # Parse sources
            sources = self._parse_sources(source_result)
            sources.extend(impl_sources)

            # Build metadata
            metadata = ContractMetadata(
                address=address,
                chain=chain,
                name=source_result.get("contract_name", "Unknown"),
                compiler_version=source_result.get("compiler_version", ""),
                optimization_enabled=source_result.get("optimization_used", "0") == "1",
                optimization_runs=int(source_result.get("runs", 0)),
                evm_version=source_result.get("evm_version", ""),
                license=source_result.get("license", ""),
                proxy_type=proxy_type,
                implementation_address=impl_address,
                abi=source_result.get("abi", []),
                sources=sources,
            )

            return FetchResult(success=True, metadata=metadata, error=None, raw_response=source_result.get("raw"))

        except Exception as e:
            return FetchResult(success=False, metadata=None, error=str(e))

    def _fetch_source(self, address: str, chain_config: ChainConfig) -> Dict:
        """Fetch source code from Etherscan API."""
        client = self._get_http_client()

        # Build API URL (Etherscan v2 API)
        params = {"chainid": chain_config.chain_id, "module": "contract", "action": "getsourcecode", "address": address, "apikey": self.api_key}

        try:
            response = client.get(chain_config.explorer_api_url or "", params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "1":
                return {"success": False, "error": data.get("message", "API error"), "raw": data}

            result = data.get("result", [])
            if not result:
                return {"success": False, "error": "No result returned", "raw": data}

            contract_data = result[0]

            # Parse ABI
            abi = []
            if contract_data.get("ABI") and contract_data["ABI"] != "Contract source code not verified":
                try:
                    abi = json.loads(contract_data["ABI"])
                except json.JSONDecodeError:
                    pass

            return {
                "success": True,
                "contract_name": contract_data.get("ContractName", ""),
                "source": contract_data.get("SourceCode", ""),
                "compiler_version": contract_data.get("CompilerVersion", ""),
                "optimization_used": contract_data.get("OptimizationUsed", "0"),
                "runs": contract_data.get("Runs", "200"),
                "evm_version": contract_data.get("EVMVersion", ""),
                "license": contract_data.get("LicenseType", ""),
                "implementation": contract_data.get("Implementation", ""),
                "abi": abi,
                "raw": data,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_sources(self, source_result: Dict) -> List[ContractSource]:
        """Parse source code from API response."""
        sources = []
        source_code = source_result.get("source", "")

        if not source_code:
            return sources

        # Check if it's a multi-file source (JSON format)
        if source_code.startswith("{{"):
            # Double-braced JSON (Etherscan format)
            try:
                source_code = source_code[1:-1]  # Remove outer braces
                parsed = json.loads(source_code)

                if isinstance(parsed, dict):
                    if "sources" in parsed:
                        # Standard Solidity JSON input format
                        for file_path, file_data in parsed["sources"].items():
                            content = file_data.get("content", "")
                            name = file_path.split("/")[-1]
                            sources.append(ContractSource(name=name, content=content, file_path=file_path))
                    else:
                        # Direct file mapping
                        for file_path, content in parsed.items():
                            if isinstance(content, str):
                                name = file_path.split("/")[-1]
                                sources.append(ContractSource(name=name, content=content, file_path=file_path))
                            elif isinstance(content, dict) and "content" in content:
                                name = file_path.split("/")[-1]
                                sources.append(ContractSource(name=name, content=content["content"], file_path=file_path))
            except json.JSONDecodeError:
                # Fall back to single file
                contract_name = source_result.get("contract_name", "Contract")
                sources.append(ContractSource(name=f"{contract_name}.sol", content=source_code, file_path=f"{contract_name}.sol"))
        elif source_code.startswith("{"):
            # Single-braced JSON
            try:
                parsed = json.loads(source_code)
                for file_path, file_data in parsed.get("sources", {}).items():
                    content = file_data.get("content", "")
                    name = file_path.split("/")[-1]
                    sources.append(ContractSource(name=name, content=content, file_path=file_path))
            except json.JSONDecodeError:
                contract_name = source_result.get("contract_name", "Contract")
                sources.append(ContractSource(name=f"{contract_name}.sol", content=source_code, file_path=f"{contract_name}.sol"))
        else:
            # Plain source code
            contract_name = source_result.get("contract_name", "Contract")
            sources.append(ContractSource(name=f"{contract_name}.sol", content=source_code, file_path=f"{contract_name}.sol"))

        return sources

    def _detect_proxy(self, address: str, chain_config: ChainConfig, source_code: str) -> Tuple[ProxyType, Optional[str]]:
        """Detect if contract is a proxy and get implementation address.

        Args:
            address: Contract address
            chain_config: Chain configuration
            source_code: Contract source code

        Returns:
            Tuple of (proxy_type, implementation_address)
        """
        # Check source code patterns first
        for proxy_type, patterns in self.PROXY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, source_code, re.IGNORECASE):
                    # Try to get implementation from storage slot
                    impl_address = self._read_implementation_slot(address, chain_config)
                    return proxy_type, impl_address

        # Check EIP-1967 slot even if not detected in source
        impl_address = self._read_implementation_slot(address, chain_config)
        if impl_address and impl_address != "0x" + "0" * 40:
            return ProxyType.EIP_1967, impl_address

        return ProxyType.NONE, None

    def _read_implementation_slot(self, address: str, chain_config: ChainConfig) -> Optional[str]:
        """Read implementation address from EIP-1967 storage slot.

        Args:
            address: Proxy contract address
            chain_config: Chain configuration

        Returns:
            Implementation address or None
        """
        if not chain_config.rpc_url:
            return None

        client = self._get_http_client()

        try:
            # eth_getStorageAt call
            payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getStorageAt", "params": [address, self.PROXY_SLOTS["implementation"], "latest"]}

            response = client.post(chain_config.rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()

            result = data.get("result", "0x")
            if result and result != "0x" and len(result) >= 42:
                # Extract address from 32-byte slot (last 20 bytes)
                impl_address = "0x" + result[-40:]
                if impl_address != "0x" + "0" * 40:
                    return impl_address

        except Exception:
            pass

        return None

    def flatten(self, sources: List[ContractSource]) -> str:
        """Flatten multiple source files into a single file.

        Args:
            sources: List of source files

        Returns:
            Flattened source code
        """
        if not sources:
            return ""

        if len(sources) == 1:
            return sources[0].content

        flattened_lines = []
        seen_pragmas = set()
        seen_imports = set()

        for source in sources:
            lines = source.content.split("\n")

            for line in lines:
                stripped = line.strip()

                # Handle pragma
                if stripped.startswith("pragma"):
                    if stripped not in seen_pragmas:
                        seen_pragmas.add(stripped)
                        flattened_lines.append(line)
                # Skip imports (already included)
                elif stripped.startswith("import"):
                    seen_imports.add(stripped)
                    continue
                else:
                    flattened_lines.append(line)

            flattened_lines.append("")  # Add separator between files

        return "\n".join(flattened_lines)

    def get_combined_source(self, result: FetchResult) -> str:
        """Get combined source code from a fetch result.

        Args:
            result: Fetch result

        Returns:
            Combined source code string
        """
        if not result.success or not result.metadata:
            return ""

        return self.flatten(result.metadata.sources)

    def fetch_multiple(self, addresses: List[Tuple[str, str]]) -> List[FetchResult]:
        """Fetch multiple contracts.

        Args:
            addresses: List of (address, chain) tuples

        Returns:
            List of fetch results
        """
        results = []
        for address, chain in addresses:
            result = self.fetch(address, chain)
            results.append(result)
        return results

    def get_supported_chains(self) -> List[str]:
        """Get list of supported chain names."""
        return list(SUPPORTED_CHAINS.keys())

    def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> "ContractFetcher":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
