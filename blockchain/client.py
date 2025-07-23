"""
Blockchain Client - A1 Agentic System

Unified blockchain client interface for Ethereum and BSC networks.
Provides comprehensive blockchain interaction capabilities using Alchemy endpoints
with advanced caching, retry mechanisms, and performance optimization.

Based on the A1 research paper specifications.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from decimal import Decimal
import aiohttp
from web3 import Web3, AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
import hashlib
from collections import defaultdict
import backoff

logger = logging.getLogger(__name__)

class NetworkType(Enum):
    """Supported blockchain networks"""
    ETHEREUM = "ethereum"
    BSC = "bsc"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"

class TransactionStatus(Enum):
    """Transaction status types"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERTED = "reverted"

@dataclass
class NetworkConfig:
    """Network configuration"""
    name: str
    network_type: NetworkType
    rpc_url: str
    chain_id: int
    explorer_url: str
    native_token: str
    block_time: float
    gas_price_multiplier: float

@dataclass
class BlockInfo:
    """Block information"""
    number: int
    hash: str
    timestamp: int
    gas_limit: int
    gas_used: int
    base_fee_per_gas: Optional[int]
    transactions: List[str]
    parent_hash: str
    miner: str

@dataclass
class TransactionInfo:
    """Transaction information"""
    hash: str
    block_number: Optional[int]
    block_hash: Optional[str]
    transaction_index: Optional[int]
    from_address: str
    to_address: Optional[str]
    value: int
    gas: int
    gas_price: int
    gas_used: Optional[int]
    status: TransactionStatus
    input_data: str
    logs: List[Dict[str, Any]]
    contract_address: Optional[str]

@dataclass
class ContractInfo:
    """Smart contract information"""
    address: str
    bytecode: str
    creation_transaction: Optional[str]
    creator_address: Optional[str]
    creation_block: Optional[int]
    is_verified: bool
    abi: Optional[List[Dict[str, Any]]]
    source_code: Optional[str]

@dataclass
class TokenInfo:
    """Token information"""
    address: str
    name: str
    symbol: str
    decimals: int
    total_supply: Optional[int]
    contract_info: Optional[ContractInfo]

class BlockchainClient:
    """
    Unified blockchain client for multiple networks.
    
    Provides comprehensive blockchain interaction capabilities with advanced
    caching, retry mechanisms, and performance optimization for exploit analysis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the blockchain client.
        
        Args:
            config: Configuration dictionary with network settings and API keys
        """
        self.config = config
        
        self.networks = self._initialize_networks()
        
        self.web3_instances: Dict[NetworkType, AsyncWeb3] = {}
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        self.block_cache: Dict[str, BlockInfo] = {}
        self.transaction_cache: Dict[str, TransactionInfo] = {}
        self.contract_cache: Dict[str, ContractInfo] = {}
        self.token_cache: Dict[str, TokenInfo] = {}
        
        self.request_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        self.rate_limits: Dict[NetworkType, Dict[str, Any]] = defaultdict(dict)
        self.last_request_time: Dict[NetworkType, float] = defaultdict(float)
        
        self._initialize_web3_instances()
    
    def _initialize_networks(self) -> Dict[NetworkType, NetworkConfig]:
        """Initialize network configurations."""
        return {
            NetworkType.ETHEREUM: NetworkConfig(
                name="Ethereum Mainnet",
                network_type=NetworkType.ETHEREUM,
                rpc_url=self.config.get('ETHEREUM_RPC_URL', 'https://eth-mainnet.g.alchemy.com/v2/QMEap6jyoJPkSgcqeWBIHfSbWv_zFiog'),
                chain_id=1,
                explorer_url="https://etherscan.io",
                native_token="ETH",
                block_time=12.0,
                gas_price_multiplier=1.1
            ),
            
            NetworkType.BSC: NetworkConfig(
                name="Binance Smart Chain",
                network_type=NetworkType.BSC,
                rpc_url=self.config.get('BSC_RPC_URL', 'https://bnb-mainnet.g.alchemy.com/v2/QMEap6jyoJPkSgcqeWBIHfSbWv_zFiog'),
                chain_id=56,
                explorer_url="https://bscscan.com",
                native_token="BNB",
                block_time=3.0,
                gas_price_multiplier=1.2
            )
        }
    
    def _initialize_web3_instances(self):
        """Initialize Web3 instances for each network."""
        for network_type, network_config in self.networks.items():
            try:
                w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(network_config.rpc_url))
                
                if network_type == NetworkType.BSC:
                    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                
                self.web3_instances[network_type] = w3
                logger.info(f"Initialized Web3 instance for {network_config.name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize Web3 for {network_config.name}: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=20)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def _make_rpc_call(self, network: NetworkType, method: str, params: List[Any]) -> Any:
        """
        Make RPC call to blockchain network with retry logic.
        
        Args:
            network: Target network
            method: RPC method name
            params: Method parameters
            
        Returns:
            RPC response data
        """
        if not self.session:
            raise RuntimeError("HTTP session not initialized. Use async context manager.")
        
        network_config = self.networks[network]
        
        await self._enforce_rate_limit(network)
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_count
        }
        
        self.request_count += 1
        
        try:
            async with self.session.post(
                network_config.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if "error" in data:
                    raise Exception(f"RPC error: {data['error']}")
                
                return data.get("result")
                
        except Exception as e:
            logger.error(f"RPC call failed for {network.value}: {e}")
            raise
    
    async def _enforce_rate_limit(self, network: NetworkType):
        """Enforce rate limiting for network requests."""
        current_time = time.time()
        last_request = self.last_request_time[network]
        
        min_interval = 0.1
        
        if current_time - last_request < min_interval:
            await asyncio.sleep(min_interval - (current_time - last_request))
        
        self.last_request_time[network] = time.time()
    
    async def get_latest_block(self, network: NetworkType) -> BlockInfo:
        """
        Get latest block information.
        
        Args:
            network: Target network
            
        Returns:
            Latest block information
        """
        block_data = await self._make_rpc_call(network, "eth_getBlockByNumber", ["latest", False])
        return self._parse_block_data(block_data)
    
    async def get_block_by_number(self, network: NetworkType, block_number: int, include_transactions: bool = False) -> BlockInfo:
        """
        Get block by number.
        
        Args:
            network: Target network
            block_number: Block number
            include_transactions: Whether to include full transaction data
            
        Returns:
            Block information
        """
        cache_key = f"{network.value}_{block_number}_{include_transactions}"
        
        if cache_key in self.block_cache:
            self.cache_hits += 1
            return self.block_cache[cache_key]
        
        self.cache_misses += 1
        
        hex_block_number = hex(block_number)
        block_data = await self._make_rpc_call(
            network, 
            "eth_getBlockByNumber", 
            [hex_block_number, include_transactions]
        )
        
        block_info = self._parse_block_data(block_data)
        
        self.block_cache[cache_key] = block_info
        
        return block_info
    
    async def get_transaction(self, network: NetworkType, tx_hash: str) -> TransactionInfo:
        """
        Get transaction information.
        
        Args:
            network: Target network
            tx_hash: Transaction hash
            
        Returns:
            Transaction information
        """
        cache_key = f"{network.value}_{tx_hash}"
        
        if cache_key in self.transaction_cache:
            self.cache_hits += 1
            return self.transaction_cache[cache_key]
        
        self.cache_misses += 1
        
        tx_data = await self._make_rpc_call(network, "eth_getTransactionByHash", [tx_hash])
        
        if not tx_data:
            raise ValueError(f"Transaction {tx_hash} not found")
        
        receipt_data = await self._make_rpc_call(network, "eth_getTransactionReceipt", [tx_hash])
        
        tx_info = self._parse_transaction_data(tx_data, receipt_data)
        
        self.transaction_cache[cache_key] = tx_info
        
        return tx_info
    
    async def get_contract_code(self, network: NetworkType, contract_address: str, block_number: Optional[int] = None) -> str:
        """
        Get contract bytecode.
        
        Args:
            network: Target network
            contract_address: Contract address
            block_number: Optional block number (latest if None)
            
        Returns:
            Contract bytecode
        """
        block_param = hex(block_number) if block_number else "latest"
        
        bytecode = await self._make_rpc_call(
            network,
            "eth_getCode",
            [contract_address, block_param]
        )
        
        return bytecode
    
    async def get_storage_at(self, network: NetworkType, contract_address: str, storage_slot: str, block_number: Optional[int] = None) -> str:
        """
        Get storage value at specific slot.
        
        Args:
            network: Target network
            contract_address: Contract address
            storage_slot: Storage slot (hex string)
            block_number: Optional block number (latest if None)
            
        Returns:
            Storage value
        """
        block_param = hex(block_number) if block_number else "latest"
        
        storage_value = await self._make_rpc_call(
            network,
            "eth_getStorageAt",
            [contract_address, storage_slot, block_param]
        )
        
        return storage_value
    
    async def get_balance(self, network: NetworkType, address: str, block_number: Optional[int] = None) -> int:
        """
        Get account balance.
        
        Args:
            network: Target network
            address: Account address
            block_number: Optional block number (latest if None)
            
        Returns:
            Balance in wei
        """
        block_param = hex(block_number) if block_number else "latest"
        
        balance_hex = await self._make_rpc_call(
            network,
            "eth_getBalance",
            [address, block_param]
        )
        
        return int(balance_hex, 16)
    
    async def call_contract(self, network: NetworkType, to_address: str, data: str, from_address: Optional[str] = None, block_number: Optional[int] = None) -> str:
        """
        Make a contract call.
        
        Args:
            network: Target network
            to_address: Contract address
            data: Call data
            from_address: Optional sender address
            block_number: Optional block number (latest if None)
            
        Returns:
            Call result
        """
        call_params = {
            "to": to_address,
            "data": data
        }
        
        if from_address:
            call_params["from"] = from_address
        
        block_param = hex(block_number) if block_number else "latest"
        
        result = await self._make_rpc_call(
            network,
            "eth_call",
            [call_params, block_param]
        )
        
        return result
    
    async def estimate_gas(self, network: NetworkType, transaction: Dict[str, Any]) -> int:
        """
        Estimate gas for transaction.
        
        Args:
            network: Target network
            transaction: Transaction parameters
            
        Returns:
            Estimated gas amount
        """
        gas_hex = await self._make_rpc_call(
            network,
            "eth_estimateGas",
            [transaction]
        )
        
        return int(gas_hex, 16)
    
    async def get_gas_price(self, network: NetworkType) -> int:
        """
        Get current gas price.
        
        Args:
            network: Target network
            
        Returns:
            Gas price in wei
        """
        gas_price_hex = await self._make_rpc_call(network, "eth_gasPrice", [])
        return int(gas_price_hex, 16)
    
    async def get_transaction_count(self, network: NetworkType, address: str, block_number: Optional[int] = None) -> int:
        """
        Get transaction count (nonce) for address.
        
        Args:
            network: Target network
            address: Account address
            block_number: Optional block number (latest if None)
            
        Returns:
            Transaction count
        """
        block_param = hex(block_number) if block_number else "latest"
        
        count_hex = await self._make_rpc_call(
            network,
            "eth_getTransactionCount",
            [address, block_param]
        )
        
        return int(count_hex, 16)
    
    async def send_raw_transaction(self, network: NetworkType, signed_tx: str) -> str:
        """
        Send raw signed transaction.
        
        Args:
            network: Target network
            signed_tx: Signed transaction data
            
        Returns:
            Transaction hash
        """
        tx_hash = await self._make_rpc_call(
            network,
            "eth_sendRawTransaction",
            [signed_tx]
        )
        
        return tx_hash
    
    async def get_logs(self, network: NetworkType, filter_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get logs matching filter criteria.
        
        Args:
            network: Target network
            filter_params: Filter parameters
            
        Returns:
            List of matching logs
        """
        logs = await self._make_rpc_call(network, "eth_getLogs", [filter_params])
        return logs
    
    async def trace_transaction(self, network: NetworkType, tx_hash: str) -> List[Dict[str, Any]]:
        """
        Trace transaction execution (if supported by node).
        
        Args:
            network: Target network
            tx_hash: Transaction hash
            
        Returns:
            Transaction trace
        """
        try:
            trace = await self._make_rpc_call(network, "debug_traceTransaction", [tx_hash])
            return trace
        except Exception as e:
            logger.warning(f"Transaction tracing not supported or failed: {e}")
            return []
    
    def _parse_block_data(self, block_data: Dict[str, Any]) -> BlockInfo:
        """Parse raw block data into BlockInfo object."""
        return BlockInfo(
            number=int(block_data["number"], 16),
            hash=block_data["hash"],
            timestamp=int(block_data["timestamp"], 16),
            gas_limit=int(block_data["gasLimit"], 16),
            gas_used=int(block_data["gasUsed"], 16),
            base_fee_per_gas=int(block_data["baseFeePerGas"], 16) if "baseFeePerGas" in block_data else None,
            transactions=block_data["transactions"],
            parent_hash=block_data["parentHash"],
            miner=block_data["miner"]
        )
    
    def _parse_transaction_data(self, tx_data: Dict[str, Any], receipt_data: Optional[Dict[str, Any]] = None) -> TransactionInfo:
        """Parse raw transaction data into TransactionInfo object."""
        status = TransactionStatus.PENDING
        gas_used = None
        logs = []
        contract_address = None
        
        if receipt_data:
            status_code = int(receipt_data.get("status", "0x0"), 16)
            if status_code == 1:
                status = TransactionStatus.CONFIRMED
            else:
                status = TransactionStatus.FAILED
            
            gas_used = int(receipt_data["gasUsed"], 16)
            logs = receipt_data.get("logs", [])
            contract_address = receipt_data.get("contractAddress")
        
        return TransactionInfo(
            hash=tx_data["hash"],
            block_number=int(tx_data["blockNumber"], 16) if tx_data.get("blockNumber") else None,
            block_hash=tx_data.get("blockHash"),
            transaction_index=int(tx_data["transactionIndex"], 16) if tx_data.get("transactionIndex") else None,
            from_address=tx_data["from"],
            to_address=tx_data.get("to"),
            value=int(tx_data["value"], 16),
            gas=int(tx_data["gas"], 16),
            gas_price=int(tx_data["gasPrice"], 16),
            gas_used=gas_used,
            status=status,
            input_data=tx_data["input"],
            logs=logs,
            contract_address=contract_address
        )
    
    async def get_contract_creation_info(self, network: NetworkType, contract_address: str) -> Optional[Dict[str, Any]]:
        """
        Get contract creation information.
        
        Args:
            network: Target network
            contract_address: Contract address
            
        Returns:
            Contract creation info or None if not found
        """
        try:
            
            bytecode = await self.get_contract_code(network, contract_address)
            
            if bytecode == "0x":
                return None  # Not a contract
            
            return {
                "address": contract_address,
                "bytecode": bytecode,
                "creation_transaction": None,  # Would need block scanning
                "creator_address": None,  # Would need block scanning
                "creation_block": None  # Would need block scanning
            }
            
        except Exception as e:
            logger.error(f"Failed to get contract creation info: {e}")
            return None
    
    async def batch_call(self, network: NetworkType, calls: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute multiple RPC calls in batch.
        
        Args:
            network: Target network
            calls: List of RPC call specifications
            
        Returns:
            List of results
        """
        if not self.session:
            raise RuntimeError("HTTP session not initialized. Use async context manager.")
        
        network_config = self.networks[network]
        
        await self._enforce_rate_limit(network)
        
        batch_payload = []
        for i, call in enumerate(calls):
            payload = {
                "jsonrpc": "2.0",
                "method": call["method"],
                "params": call["params"],
                "id": self.request_count + i
            }
            batch_payload.append(payload)
        
        self.request_count += len(calls)
        
        try:
            async with self.session.post(
                network_config.rpc_url,
                json=batch_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                results = []
                for item in data:
                    if "error" in item:
                        results.append({"error": item["error"]})
                    else:
                        results.append(item.get("result"))
                
                return results
                
        except Exception as e:
            logger.error(f"Batch RPC call failed for {network.value}: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get client performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / max(total_requests, 1)
        
        return {
            "total_requests": self.request_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": cache_hit_rate,
            "cached_blocks": len(self.block_cache),
            "cached_transactions": len(self.transaction_cache),
            "cached_contracts": len(self.contract_cache),
            "cached_tokens": len(self.token_cache)
        }
    
    async def cleanup_cache(self, max_age_seconds: int = 3600):
        """Clean up old cache entries."""
        current_time = time.time()
        
        
        if len(self.block_cache) > 1000:
            sorted_keys = sorted(self.block_cache.keys())
            keys_to_remove = sorted_keys[:-500]
            for key in keys_to_remove:
                del self.block_cache[key]
        
        if len(self.transaction_cache) > 1000:
            sorted_keys = sorted(self.transaction_cache.keys())
            keys_to_remove = sorted_keys[:-500]
            for key in keys_to_remove:
                del self.transaction_cache[key]
        
        logger.info("Cache cleanup completed")
    def get_web3(self, network: str) -> Web3:
        """
        Get Web3 instance for a specific network.
        
        Args:
            network: Network name ('ethereum' or 'bsc')
            
        Returns:
            Web3 instance for the specified network
        """
        if network.lower() == 'ethereum':
            return self.web3_instances[NetworkType.ETHEREUM]
        elif network.lower() == 'bsc':
            return self.web3_instances[NetworkType.BSC]
        else:
            raise ValueError(f"Unsupported network: {network}")

    
    async def close(self):
        """Close the blockchain client and cleanup resources."""
        if self.session:
            await self.session.close()
        
        self.block_cache.clear()
        self.transaction_cache.clear()
        self.contract_cache.clear()
        self.token_cache.clear()
        
        logger.info("Blockchain client closed")
