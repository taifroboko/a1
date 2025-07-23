"""
Scanner Integration - A1 Agentic System

Integrates with Etherscan and BSCscan APIs for contract source code retrieval,
verification status checking, and comprehensive contract analysis.

Based on the A1 research paper specifications.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import aiohttp
import backoff
from collections import defaultdict

logger = logging.getLogger(__name__)

class ScannerType(Enum):
    """Supported blockchain scanners"""
    ETHERSCAN = "etherscan"
    BSCSCAN = "bscscan"
    POLYGONSCAN = "polygonscan"

class VerificationStatus(Enum):
    """Contract verification status"""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    PROXY = "proxy"

@dataclass
class ContractSourceInfo:
    """Contract source code information"""
    address: str
    source_code: str
    abi: List[Dict[str, Any]]
    contract_name: str
    compiler_version: str
    optimization_enabled: bool
    optimization_runs: int
    constructor_arguments: str
    library_info: Dict[str, str]
    proxy_implementation: Optional[str]
    verification_status: VerificationStatus
    creation_bytecode: Optional[str]
    swarm_source: Optional[str]

@dataclass
class TransactionDetails:
    """Detailed transaction information from scanner"""
    hash: str
    block_number: int
    timestamp: int
    from_address: str
    to_address: Optional[str]
    value: str
    gas: int
    gas_price: str
    gas_used: int
    status: str
    input_data: str
    method_id: Optional[str]
    function_name: Optional[str]
    logs: List[Dict[str, Any]]
    internal_transactions: List[Dict[str, Any]]

@dataclass
class TokenInfo:
    """Token information from scanner"""
    address: str
    name: str
    symbol: str
    decimals: int
    total_supply: str
    contract_address: str
    token_type: str
    holders_count: Optional[int]
    transfers_count: Optional[int]

class BlockchainScanner:
    """
    Unified blockchain scanner for multiple networks.
    
    Provides comprehensive contract analysis capabilities using various
    blockchain explorer APIs with advanced caching and rate limiting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the blockchain scanner.
        
        Args:
            config: Configuration dictionary with API keys and settings
        """
        self.config = config
        
        self.scanners = self._initialize_scanners()
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        self.source_code_cache: Dict[str, ContractSourceInfo] = {}
        self.transaction_cache: Dict[str, TransactionDetails] = {}
        self.token_cache: Dict[str, TokenInfo] = {}
        
        self.rate_limits: Dict[ScannerType, Dict[str, Any]] = defaultdict(dict)
        self.last_request_time: Dict[ScannerType, float] = defaultdict(float)
        
        self.request_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _initialize_scanners(self) -> Dict[ScannerType, Dict[str, Any]]:
        """Initialize scanner configurations."""
        return {
            ScannerType.ETHERSCAN: {
                "base_url": "https://api.etherscan.io/api",
                "api_key": self.config.get('ETHERSCAN_API_KEY', '5UWN6DNT7UZCEJYNE3J6FCVAWH4QJW255K'),
                "rate_limit": 5,  # requests per second
                "timeout": 30
            },
            
            ScannerType.BSCSCAN: {
                "base_url": "https://api.bscscan.com/api",
                "api_key": self.config.get('BSCSCAN_API_KEY', '8N6QAZ34G96WP8IE5JZ48KDQU4JG3GF8KR'),
                "rate_limit": 5,  # requests per second
                "timeout": 30
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=10)
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
    async def _make_api_call(self, scanner: ScannerType, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API call to blockchain scanner with retry logic.
        
        Args:
            scanner: Target scanner
            params: API parameters
            
        Returns:
            API response data
        """
        if not self.session:
            raise RuntimeError("HTTP session not initialized. Use async context manager.")
        
        scanner_config = self.scanners[scanner]
        
        await self._enforce_rate_limit(scanner)
        
        params["apikey"] = scanner_config["api_key"]
        
        self.request_count += 1
        
        try:
            async with self.session.get(
                scanner_config["base_url"],
                params=params,
                timeout=aiohttp.ClientTimeout(total=scanner_config["timeout"])
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data.get("status") == "0" and "error" in data.get("message", "").lower():
                    raise Exception(f"Scanner API error: {data.get('message', 'Unknown error')}")
                
                return data
                
        except Exception as e:
            logger.error(f"Scanner API call failed for {scanner.value}: {e}")
            raise
    
    async def _enforce_rate_limit(self, scanner: ScannerType):
        """Enforce rate limiting for scanner requests."""
        current_time = time.time()
        last_request = self.last_request_time[scanner]
        
        scanner_config = self.scanners[scanner]
        min_interval = 1.0 / scanner_config["rate_limit"]
        
        if current_time - last_request < min_interval:
            await asyncio.sleep(min_interval - (current_time - last_request))
        
        self.last_request_time[scanner] = time.time()
    
    async def get_contract_source_code(self, scanner: ScannerType, contract_address: str) -> Optional[ContractSourceInfo]:
        """
        Get contract source code and verification information.
        
        Args:
            scanner: Target scanner
            contract_address: Contract address
            
        Returns:
            Contract source information or None if not found
        """
        cache_key = f"{scanner.value}_{contract_address.lower()}"
        
        if cache_key in self.source_code_cache:
            self.cache_hits += 1
            return self.source_code_cache[cache_key]
        
        self.cache_misses += 1
        
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": contract_address
        }
        
        try:
            response = await self._make_api_call(scanner, params)
            
            if response.get("status") == "1" and response.get("result"):
                result = response["result"][0]
                
                if not result.get("SourceCode"):
                    return None
                
                source_code = result["SourceCode"]
                if source_code.startswith("{{"):
                    try:
                        source_json = json.loads(source_code[1:-1])  # Remove outer braces
                        if "sources" in source_json:
                            combined_source = ""
                            for file_path, file_info in source_json["sources"].items():
                                combined_source += f"// File: {file_path}\n"
                                combined_source += file_info.get("content", "") + "\n\n"
                            source_code = combined_source
                    except json.JSONDecodeError:
                        pass  # Use original source code
                
                abi = []
                if result.get("ABI") and result["ABI"] != "Contract source code not verified":
                    try:
                        abi = json.loads(result["ABI"])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse ABI for {contract_address}")
                
                verification_status = VerificationStatus.VERIFIED
                if result.get("Proxy") == "1":
                    verification_status = VerificationStatus.PROXY
                
                library_info = {}
                for i in range(1, 11):  # Check Library1 to Library10
                    lib_name = result.get(f"Library{i}Name")
                    lib_address = result.get(f"Library{i}Address")
                    if lib_name and lib_address:
                        library_info[lib_name] = lib_address
                
                contract_info = ContractSourceInfo(
                    address=contract_address,
                    source_code=source_code,
                    abi=abi,
                    contract_name=result.get("ContractName", ""),
                    compiler_version=result.get("CompilerVersion", ""),
                    optimization_enabled=result.get("OptimizationUsed") == "1",
                    optimization_runs=int(result.get("Runs", "0")),
                    constructor_arguments=result.get("ConstructorArguments", ""),
                    library_info=library_info,
                    proxy_implementation=result.get("Implementation") if result.get("Proxy") == "1" else None,
                    verification_status=verification_status,
                    creation_bytecode=None,  # Not provided by this API
                    swarm_source=result.get("SwarmSource")
                )
                
                self.source_code_cache[cache_key] = contract_info
                
                return contract_info
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get source code for {contract_address}: {e}")
            return None
    
    async def get_contract_abi(self, scanner: ScannerType, contract_address: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get contract ABI.
        
        Args:
            scanner: Target scanner
            contract_address: Contract address
            
        Returns:
            Contract ABI or None if not found
        """
        params = {
            "module": "contract",
            "action": "getabi",
            "address": contract_address
        }
        
        try:
            response = await self._make_api_call(scanner, params)
            
            if response.get("status") == "1" and response.get("result"):
                abi_string = response["result"]
                if abi_string != "Contract source code not verified":
                    return json.loads(abi_string)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get ABI for {contract_address}: {e}")
            return None
    
    async def get_transaction_details(self, scanner: ScannerType, tx_hash: str) -> Optional[TransactionDetails]:
        """
        Get detailed transaction information.
        
        Args:
            scanner: Target scanner
            tx_hash: Transaction hash
            
        Returns:
            Transaction details or None if not found
        """
        cache_key = f"{scanner.value}_{tx_hash}"
        
        if cache_key in self.transaction_cache:
            self.cache_hits += 1
            return self.transaction_cache[cache_key]
        
        self.cache_misses += 1
        
        tx_params = {
            "module": "proxy",
            "action": "eth_getTransactionByHash",
            "txhash": tx_hash
        }
        
        receipt_params = {
            "module": "proxy",
            "action": "eth_getTransactionReceipt",
            "txhash": tx_hash
        }
        
        try:
            tx_response, receipt_response = await asyncio.gather(
                self._make_api_call(scanner, tx_params),
                self._make_api_call(scanner, receipt_params)
            )
            
            if not (tx_response.get("result") and receipt_response.get("result")):
                return None
            
            tx_data = tx_response["result"]
            receipt_data = receipt_response["result"]
            
            internal_txs = await self._get_internal_transactions(scanner, tx_hash)
            
            method_id = None
            function_name = None
            if tx_data.get("input") and len(tx_data["input"]) >= 10:
                method_id = tx_data["input"][:10]
            
            transaction_details = TransactionDetails(
                hash=tx_hash,
                block_number=int(tx_data["blockNumber"], 16),
                timestamp=0,  # Would need block info to get timestamp
                from_address=tx_data["from"],
                to_address=tx_data.get("to"),
                value=tx_data["value"],
                gas=int(tx_data["gas"], 16),
                gas_price=tx_data["gasPrice"],
                gas_used=int(receipt_data["gasUsed"], 16),
                status=receipt_data["status"],
                input_data=tx_data["input"],
                method_id=method_id,
                function_name=function_name,
                logs=receipt_data.get("logs", []),
                internal_transactions=internal_txs
            )
            
            self.transaction_cache[cache_key] = transaction_details
            
            return transaction_details
            
        except Exception as e:
            logger.error(f"Failed to get transaction details for {tx_hash}: {e}")
            return None
    
    async def _get_internal_transactions(self, scanner: ScannerType, tx_hash: str) -> List[Dict[str, Any]]:
        """Get internal transactions for a transaction hash."""
        params = {
            "module": "account",
            "action": "txlistinternal",
            "txhash": tx_hash
        }
        
        try:
            response = await self._make_api_call(scanner, params)
            
            if response.get("status") == "1" and response.get("result"):
                return response["result"]
            
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get internal transactions for {tx_hash}: {e}")
            return []
    
    async def get_contract_creation_info(self, scanner: ScannerType, contract_address: str) -> Optional[Dict[str, Any]]:
        """
        Get contract creation transaction information.
        
        Args:
            scanner: Target scanner
            contract_address: Contract address
            
        Returns:
            Contract creation info or None if not found
        """
        params = {
            "module": "contract",
            "action": "getcontractcreation",
            "contractaddresses": contract_address
        }
        
        try:
            response = await self._make_api_call(scanner, params)
            
            if response.get("status") == "1" and response.get("result"):
                result = response["result"][0]
                return {
                    "contract_address": result.get("contractAddress"),
                    "contract_creator": result.get("contractCreator"),
                    "tx_hash": result.get("txHash")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get contract creation info for {contract_address}: {e}")
            return None
    
    async def get_token_info(self, scanner: ScannerType, token_address: str) -> Optional[TokenInfo]:
        """
        Get token information.
        
        Args:
            scanner: Target scanner
            token_address: Token contract address
            
        Returns:
            Token information or None if not found
        """
        cache_key = f"{scanner.value}_token_{token_address.lower()}"
        
        if cache_key in self.token_cache:
            self.cache_hits += 1
            return self.token_cache[cache_key]
        
        self.cache_misses += 1
        
        supply_params = {
            "module": "stats",
            "action": "tokensupply",
            "contractaddress": token_address
        }
        
        try:
            supply_response = await self._make_api_call(scanner, supply_params)
            
            if supply_response.get("status") == "1":
                total_supply = supply_response.get("result", "0")
                
                contract_info = await self.get_contract_source_code(scanner, token_address)
                
                if contract_info:
                    name = ""
                    symbol = ""
                    decimals = 18  # Default
                    
                    for item in contract_info.abi:
                        if item.get("type") == "function":
                            if item.get("name") == "name":
                                pass
                            elif item.get("name") == "symbol":
                                pass
                            elif item.get("name") == "decimals":
                                pass
                    
                    token_info = TokenInfo(
                        address=token_address,
                        name=name or "Unknown",
                        symbol=symbol or "UNK",
                        decimals=decimals,
                        total_supply=total_supply,
                        contract_address=token_address,
                        token_type="ERC20",  # Assume ERC20 for now
                        holders_count=None,  # Not available from this API
                        transfers_count=None  # Not available from this API
                    )
                    
                    self.token_cache[cache_key] = token_info
                    
                    return token_info
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get token info for {token_address}: {e}")
            return None
    
    async def get_contract_transactions(self, scanner: ScannerType, contract_address: str, start_block: int = 0, end_block: int = 999999999, page: int = 1, offset: int = 100) -> List[Dict[str, Any]]:
        """
        Get transactions for a contract address.
        
        Args:
            scanner: Target scanner
            contract_address: Contract address
            start_block: Starting block number
            end_block: Ending block number
            page: Page number
            offset: Number of transactions per page
            
        Returns:
            List of transactions
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": contract_address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": "desc"
        }
        
        try:
            response = await self._make_api_call(scanner, params)
            
            if response.get("status") == "1" and response.get("result"):
                return response["result"]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get transactions for {contract_address}: {e}")
            return []
    
    async def get_contract_events(self, scanner: ScannerType, contract_address: str, topic0: Optional[str] = None, start_block: int = 0, end_block: int = 999999999) -> List[Dict[str, Any]]:
        """
        Get events/logs for a contract address.
        
        Args:
            scanner: Target scanner
            contract_address: Contract address
            topic0: Optional event signature hash
            start_block: Starting block number
            end_block: Ending block number
            
        Returns:
            List of events/logs
        """
        params = {
            "module": "logs",
            "action": "getLogs",
            "address": contract_address,
            "fromBlock": start_block,
            "toBlock": end_block
        }
        
        if topic0:
            params["topic0"] = topic0
        
        try:
            response = await self._make_api_call(scanner, params)
            
            if response.get("status") == "1" and response.get("result"):
                return response["result"]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get events for {contract_address}: {e}")
            return []
    
    async def batch_get_source_codes(self, scanner: ScannerType, contract_addresses: List[str]) -> Dict[str, Optional[ContractSourceInfo]]:
        """
        Get source codes for multiple contracts in batch.
        
        Args:
            scanner: Target scanner
            contract_addresses: List of contract addresses
            
        Returns:
            Dictionary mapping addresses to source info
        """
        results = {}
        
        batch_size = 5
        for i in range(0, len(contract_addresses), batch_size):
            batch = contract_addresses[i:i + batch_size]
            
            tasks = [
                self.get_contract_source_code(scanner, address)
                for address in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for address, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to get source for {address}: {result}")
                    results[address] = None
                else:
                    results[address] = result
            
            if i + batch_size < len(contract_addresses):
                await asyncio.sleep(1)
        
        return results
    
    def get_scanner_for_network(self, network_name: str) -> Optional[ScannerType]:
        """
        Get appropriate scanner for network name.
        
        Args:
            network_name: Network name (ethereum, bsc, etc.)
            
        Returns:
            Scanner type or None if not supported
        """
        network_mapping = {
            "ethereum": ScannerType.ETHERSCAN,
            "eth": ScannerType.ETHERSCAN,
            "mainnet": ScannerType.ETHERSCAN,
            "bsc": ScannerType.BSCSCAN,
            "binance": ScannerType.BSCSCAN,
            "bnb": ScannerType.BSCSCAN
        }
        
        return network_mapping.get(network_name.lower())
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get scanner performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / max(total_requests, 1)
        
        return {
            "total_requests": self.request_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": cache_hit_rate,
            "cached_source_codes": len(self.source_code_cache),
            "cached_transactions": len(self.transaction_cache),
            "cached_tokens": len(self.token_cache)
        }
    
    async def cleanup_cache(self, max_age_seconds: int = 3600):
        """Clean up old cache entries."""
        current_time = time.time()
        
        if len(self.source_code_cache) > 1000:
            sorted_keys = sorted(self.source_code_cache.keys())
            keys_to_remove = sorted_keys[:-500]
            for key in keys_to_remove:
                del self.source_code_cache[key]
        
        if len(self.transaction_cache) > 1000:
            sorted_keys = sorted(self.transaction_cache.keys())
            keys_to_remove = sorted_keys[:-500]
            for key in keys_to_remove:
                del self.transaction_cache[key]
        
        if len(self.token_cache) > 500:
            sorted_keys = sorted(self.token_cache.keys())
            keys_to_remove = sorted_keys[:-250]
            for key in keys_to_remove:
                del self.token_cache[key]
        
        logger.info("Scanner cache cleanup completed")
    
    async def close(self):
        """Close the scanner and cleanup resources."""
        if self.session:
            await self.session.close()
        
        self.source_code_cache.clear()
        self.transaction_cache.clear()
        self.token_cache.clear()
        
        logger.info("Blockchain scanner closed")
