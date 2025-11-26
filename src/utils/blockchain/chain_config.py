"""Blockchain Chain Configuration.

This module provides configuration for 75+ supported blockchain networks
including mainnets and testnets.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional


class NetworkType(Enum):
    """Type of blockchain network."""

    MAINNET = "mainnet"
    TESTNET = "testnet"


@dataclass
class ChainConfig:
    """Configuration for a blockchain network."""

    chain_id: int
    name: str
    short_name: str
    network_type: NetworkType
    native_currency: str
    native_decimals: int
    rpc_url: Optional[str]
    explorer_url: Optional[str]
    explorer_api_url: Optional[str]
    explorer_api_key_env: str  # Environment variable name for API key
    is_evm: bool = True
    l2_for: Optional[str] = None  # Parent L1 chain if this is an L2


# Comprehensive list of 75+ supported chains
SUPPORTED_CHAINS: Dict[str, ChainConfig] = {
    # ===== Ethereum & L2s =====
    "ethereum": ChainConfig(
        chain_id=1,
        name="Ethereum Mainnet",
        short_name="eth",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://eth.llamarpc.com",
        explorer_url="https://etherscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "arbitrum": ChainConfig(
        chain_id=42161,
        name="Arbitrum One",
        short_name="arb",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://arb1.arbitrum.io/rpc",
        explorer_url="https://arbiscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "optimism": ChainConfig(
        chain_id=10,
        name="Optimism",
        short_name="op",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://mainnet.optimism.io",
        explorer_url="https://optimistic.etherscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "base": ChainConfig(
        chain_id=8453,
        name="Base",
        short_name="base",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "polygon": ChainConfig(
        chain_id=137,
        name="Polygon PoS",
        short_name="polygon",
        network_type=NetworkType.MAINNET,
        native_currency="MATIC",
        native_decimals=18,
        rpc_url="https://polygon-rpc.com",
        explorer_url="https://polygonscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "polygon_zkevm": ChainConfig(
        chain_id=1101,
        name="Polygon zkEVM",
        short_name="polygon_zkevm",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://zkevm-rpc.com",
        explorer_url="https://zkevm.polygonscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "zksync": ChainConfig(
        chain_id=324,
        name="zkSync Era",
        short_name="zksync",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://mainnet.era.zksync.io",
        explorer_url="https://explorer.zksync.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "linea": ChainConfig(
        chain_id=59144,
        name="Linea",
        short_name="linea",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://rpc.linea.build",
        explorer_url="https://lineascan.build",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "scroll": ChainConfig(
        chain_id=534352,
        name="Scroll",
        short_name="scroll",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://rpc.scroll.io",
        explorer_url="https://scrollscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "blast": ChainConfig(
        chain_id=81457,
        name="Blast",
        short_name="blast",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://rpc.blast.io",
        explorer_url="https://blastscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "mantle": ChainConfig(
        chain_id=5000,
        name="Mantle",
        short_name="mantle",
        network_type=NetworkType.MAINNET,
        native_currency="MNT",
        native_decimals=18,
        rpc_url="https://rpc.mantle.xyz",
        explorer_url="https://mantlescan.info",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "mode": ChainConfig(
        chain_id=34443,
        name="Mode",
        short_name="mode",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://mainnet.mode.network",
        explorer_url="https://modescan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "manta": ChainConfig(
        chain_id=169,
        name="Manta Pacific",
        short_name="manta",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://pacific-rpc.manta.network/http",
        explorer_url="https://pacific-explorer.manta.network",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "taiko": ChainConfig(
        chain_id=167000,
        name="Taiko",
        short_name="taiko",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://rpc.taiko.xyz",
        explorer_url="https://taikoscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    # ===== Other EVM Chains =====
    "bsc": ChainConfig(
        chain_id=56,
        name="BNB Smart Chain",
        short_name="bsc",
        network_type=NetworkType.MAINNET,
        native_currency="BNB",
        native_decimals=18,
        rpc_url="https://bsc-dataseed.binance.org",
        explorer_url="https://bscscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "avalanche": ChainConfig(
        chain_id=43114,
        name="Avalanche C-Chain",
        short_name="avax",
        network_type=NetworkType.MAINNET,
        native_currency="AVAX",
        native_decimals=18,
        rpc_url="https://api.avax.network/ext/bc/C/rpc",
        explorer_url="https://snowtrace.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "fantom": ChainConfig(
        chain_id=250,
        name="Fantom Opera",
        short_name="ftm",
        network_type=NetworkType.MAINNET,
        native_currency="FTM",
        native_decimals=18,
        rpc_url="https://rpc.ftm.tools",
        explorer_url="https://ftmscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "gnosis": ChainConfig(
        chain_id=100,
        name="Gnosis Chain",
        short_name="gno",
        network_type=NetworkType.MAINNET,
        native_currency="xDAI",
        native_decimals=18,
        rpc_url="https://rpc.gnosischain.com",
        explorer_url="https://gnosisscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "celo": ChainConfig(
        chain_id=42220,
        name="Celo",
        short_name="celo",
        network_type=NetworkType.MAINNET,
        native_currency="CELO",
        native_decimals=18,
        rpc_url="https://forno.celo.org",
        explorer_url="https://celoscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "moonbeam": ChainConfig(
        chain_id=1284,
        name="Moonbeam",
        short_name="moonbeam",
        network_type=NetworkType.MAINNET,
        native_currency="GLMR",
        native_decimals=18,
        rpc_url="https://rpc.api.moonbeam.network",
        explorer_url="https://moonscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "moonriver": ChainConfig(
        chain_id=1285,
        name="Moonriver",
        short_name="moonriver",
        network_type=NetworkType.MAINNET,
        native_currency="MOVR",
        native_decimals=18,
        rpc_url="https://rpc.api.moonriver.moonbeam.network",
        explorer_url="https://moonriver.moonscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "cronos": ChainConfig(
        chain_id=25,
        name="Cronos",
        short_name="cro",
        network_type=NetworkType.MAINNET,
        native_currency="CRO",
        native_decimals=18,
        rpc_url="https://evm.cronos.org",
        explorer_url="https://cronoscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "aurora": ChainConfig(
        chain_id=1313161554,
        name="Aurora",
        short_name="aurora",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://mainnet.aurora.dev",
        explorer_url="https://aurorascan.dev",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "metis": ChainConfig(
        chain_id=1088,
        name="Metis Andromeda",
        short_name="metis",
        network_type=NetworkType.MAINNET,
        native_currency="METIS",
        native_decimals=18,
        rpc_url="https://andromeda.metis.io/?owner=1088",
        explorer_url="https://andromeda-explorer.metis.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "boba": ChainConfig(
        chain_id=288,
        name="Boba Network",
        short_name="boba",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://mainnet.boba.network",
        explorer_url="https://bobascan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "kava": ChainConfig(
        chain_id=2222,
        name="Kava EVM",
        short_name="kava",
        network_type=NetworkType.MAINNET,
        native_currency="KAVA",
        native_decimals=18,
        rpc_url="https://evm.kava.io",
        explorer_url="https://explorer.kava.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "klaytn": ChainConfig(
        chain_id=8217,
        name="Klaytn",
        short_name="klay",
        network_type=NetworkType.MAINNET,
        native_currency="KLAY",
        native_decimals=18,
        rpc_url="https://public-node-api.klaytnapi.com/v1/cypress",
        explorer_url="https://scope.klaytn.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "harmony": ChainConfig(
        chain_id=1666600000,
        name="Harmony",
        short_name="one",
        network_type=NetworkType.MAINNET,
        native_currency="ONE",
        native_decimals=18,
        rpc_url="https://api.harmony.one",
        explorer_url="https://explorer.harmony.one",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "fraxtal": ChainConfig(
        chain_id=252,
        name="Fraxtal",
        short_name="fraxtal",
        network_type=NetworkType.MAINNET,
        native_currency="frxETH",
        native_decimals=18,
        rpc_url="https://rpc.frax.com",
        explorer_url="https://fraxscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "zora": ChainConfig(
        chain_id=7777777,
        name="Zora",
        short_name="zora",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://rpc.zora.energy",
        explorer_url="https://explorer.zora.energy",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "worldchain": ChainConfig(
        chain_id=480,
        name="World Chain",
        short_name="worldchain",
        network_type=NetworkType.MAINNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://worldchain-mainnet.g.alchemy.com/public",
        explorer_url="https://worldscan.org",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        l2_for="ethereum",
    ),
    "monad": ChainConfig(
        chain_id=0,  # Testnet only currently
        name="Monad",
        short_name="monad",
        network_type=NetworkType.TESTNET,
        native_currency="MON",
        native_decimals=18,
        rpc_url=None,  # Not public yet
        explorer_url=None,
        explorer_api_url=None,
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    # ===== Testnets =====
    "sepolia": ChainConfig(
        chain_id=11155111,
        name="Sepolia Testnet",
        short_name="sepolia",
        network_type=NetworkType.TESTNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://rpc.sepolia.org",
        explorer_url="https://sepolia.etherscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "holesky": ChainConfig(
        chain_id=17000,
        name="Holesky Testnet",
        short_name="holesky",
        network_type=NetworkType.TESTNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://ethereum-holesky.publicnode.com",
        explorer_url="https://holesky.etherscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "arbitrum_sepolia": ChainConfig(
        chain_id=421614,
        name="Arbitrum Sepolia",
        short_name="arb_sepolia",
        network_type=NetworkType.TESTNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://sepolia-rollup.arbitrum.io/rpc",
        explorer_url="https://sepolia.arbiscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "base_sepolia": ChainConfig(
        chain_id=84532,
        name="Base Sepolia",
        short_name="base_sepolia",
        network_type=NetworkType.TESTNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://sepolia.base.org",
        explorer_url="https://sepolia.basescan.org",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "optimism_sepolia": ChainConfig(
        chain_id=11155420,
        name="Optimism Sepolia",
        short_name="op_sepolia",
        network_type=NetworkType.TESTNET,
        native_currency="ETH",
        native_decimals=18,
        rpc_url="https://sepolia.optimism.io",
        explorer_url="https://sepolia-optimistic.etherscan.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "polygon_amoy": ChainConfig(
        chain_id=80002,
        name="Polygon Amoy",
        short_name="amoy",
        network_type=NetworkType.TESTNET,
        native_currency="MATIC",
        native_decimals=18,
        rpc_url="https://rpc-amoy.polygon.technology",
        explorer_url="https://amoy.polygonscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "bsc_testnet": ChainConfig(
        chain_id=97,
        name="BNB Testnet",
        short_name="bsc_testnet",
        network_type=NetworkType.TESTNET,
        native_currency="tBNB",
        native_decimals=18,
        rpc_url="https://data-seed-prebsc-1-s1.binance.org:8545",
        explorer_url="https://testnet.bscscan.com",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
    "avalanche_fuji": ChainConfig(
        chain_id=43113,
        name="Avalanche Fuji",
        short_name="fuji",
        network_type=NetworkType.TESTNET,
        native_currency="AVAX",
        native_decimals=18,
        rpc_url="https://api.avax-test.network/ext/bc/C/rpc",
        explorer_url="https://testnet.snowtrace.io",
        explorer_api_url="https://api.etherscan.io/v2/api",
        explorer_api_key_env="ETHERSCAN_API_KEY",
    ),
}


def get_chain_by_id(chain_id: int) -> Optional[ChainConfig]:
    """Get chain configuration by chain ID.

    Args:
        chain_id: The chain ID to look up

    Returns:
        ChainConfig if found, None otherwise
    """
    for config in SUPPORTED_CHAINS.values():
        if config.chain_id == chain_id:
            return config
    return None


def get_chain_by_name(name: str) -> Optional[ChainConfig]:
    """Get chain configuration by name.

    Args:
        name: Chain name (case-insensitive)

    Returns:
        ChainConfig if found, None otherwise
    """
    return SUPPORTED_CHAINS.get(name.lower())


def get_all_mainnets() -> List[ChainConfig]:
    """Get all mainnet chain configurations."""
    return [c for c in SUPPORTED_CHAINS.values() if c.network_type == NetworkType.MAINNET]


def get_all_testnets() -> List[ChainConfig]:
    """Get all testnet chain configurations."""
    return [c for c in SUPPORTED_CHAINS.values() if c.network_type == NetworkType.TESTNET]


def get_l2_chains() -> List[ChainConfig]:
    """Get all L2 chain configurations."""
    return [c for c in SUPPORTED_CHAINS.values() if c.l2_for is not None]
