"""
Source Code Fetcher Tool - A1 Agentic System

This tool implements proxy contract resolution through bytecode pattern analysis
and implementation slot examination, ensuring the agent can access actual 
executable logic rather than proxy interfaces.

Based on the A1 research paper specifications.
"""

import asyncio
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from web3 import Web3
from eth_utils import to_checksum_address, is_address
import requests
import logging

logger = logging.getLogger(__name__)

@dataclass
class ContractInfo:
    """Container for contract information"""
    address: str
    source_code: str
    abi: List[Dict]
    contract_name: Optional[str] = None
    implementation_address: Optional[str] = None
    proxy_type: Optional[str] = None
    constructor_args: Optional[str] = None
    compiler_version: Optional[str] = None
    optimization_enabled: Optional[bool] = None

class SourceCodeFetcher:
    """
    Fetches and resolves smart contract source code with proxy detection.
    
    Implements bytecode pattern analysis to identify proxy contracts and
    resolve their implementation addresses for complete source code access.
    """
    
    PROXY_PATTERNS = {
        'EIP1967': {
            'implementation_slot': '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc',
            'admin_slot': '0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103',
            'beacon_slot': '0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'
        },
        'EIP1822': {
            'implementation_slot': '0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7'
        },
        'OpenZeppelin': {
            'implementation_slot': '0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3'
        }
    }
    
    def __init__(self, web3_client: Web3, etherscan_api_key: str, bscscan_api_key: str):
        """
        Initialize the source code fetcher.
        
        Args:
            web3_client: Web3 instance for blockchain interaction
            etherscan_api_key: Etherscan API key for source code retrieval
            bscscan_api_key: BSCscan API key for source code retrieval
        """
        self.web3 = web3_client
        self.etherscan_api_key = etherscan_api_key
        self.bscscan_api_key = bscscan_api_key
        self.session = requests.Session()
        
        self.scanner_url = "https://api.etherscan.io/api"
        self.api_key = etherscan_api_key
        self.chain_id = None
    
    async def fetch_contract_source(self, address: str, block_number: Optional[int] = None) -> ContractInfo:
        """
        Fetch complete contract source code with proxy resolution.
        
        Args:
            address: Contract address to analyze
            block_number: Historical block number for temporal consistency
            
        Returns:
            ContractInfo object with complete source code and metadata
        """
        address = to_checksum_address(address)
        logger.info(f"Fetching source code for contract: {address}")
        
        if self.chain_id is None:
            try:
                if hasattr(self.web3.eth, 'chain_id'):
                    if asyncio.iscoroutine(self.web3.eth.chain_id):
                        self.chain_id = await self.web3.eth.chain_id
                    else:
                        self.chain_id = self.web3.eth.chain_id
                else:
                    self.chain_id = 1
                
                if self.chain_id == 1:  # Ethereum mainnet
                    self.scanner_url = "https://api.etherscan.io/api"
                    self.api_key = self.etherscan_api_key
                elif self.chain_id == 56:  # BSC mainnet
                    self.scanner_url = "https://api.bscscan.com/api"
                    self.api_key = self.bscscan_api_key
                else:
                    logger.warning(f"Unsupported chain ID: {self.chain_id}, defaulting to Ethereum")
                    self.chain_id = 1
                    self.scanner_url = "https://api.etherscan.io/api"
                    self.api_key = self.etherscan_api_key
            except Exception as e:
                logger.warning(f"Failed to get chain ID: {e}, defaulting to Ethereum")
                self.chain_id = 1
                self.scanner_url = "https://api.etherscan.io/api"
                self.api_key = self.etherscan_api_key
        
        contract_info = await self._fetch_from_scanner(address)
        
        proxy_info = await self._detect_proxy_pattern(address, block_number)
        
        if proxy_info:
            logger.info(f"Detected proxy contract: {proxy_info['type']}")
            contract_info.proxy_type = proxy_info['type']
            contract_info.implementation_address = proxy_info['implementation']
            
            impl_info = await self._fetch_from_scanner(proxy_info['implementation'])
            
            contract_info.source_code = f"""
// PROXY CONTRACT SOURCE CODE
// Proxy Type: {proxy_info['type']}
// Implementation: {proxy_info['implementation']}

{contract_info.source_code}

// IMPLEMENTATION CONTRACT SOURCE CODE
{impl_info.source_code}
"""
            contract_info.abi = impl_info.abi
        
        return contract_info
    
    async def _fetch_from_scanner(self, address: str) -> ContractInfo:
        """Fetch contract source code from blockchain scanner API."""
        params = {
            'module': 'contract',
            'action': 'getsourcecode',
            'address': address,
            'apikey': self.api_key
        }
        
        response = await self._make_request(self.scanner_url, params)
        
        if not response or response['status'] != '1':
            raise ValueError(f"Failed to fetch source code for {address}")
        
        result = response['result'][0]
        
        abi = []
        if result.get('ABI') and result['ABI'] != 'Contract source code not verified':
            try:
                import json
                abi = json.loads(result['ABI'])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse ABI for {address}")
        
        return ContractInfo(
            address=address,
            source_code=result.get('SourceCode', ''),
            abi=abi,
            contract_name=result.get('ContractName', 'Unknown'),
            constructor_args=result.get('ConstructorArguments'),
            compiler_version=result.get('CompilerVersion'),
            optimization_enabled=result.get('OptimizationUsed') == '1'
        )
    
    async def _detect_proxy_pattern(self, address: str, block_number: Optional[int] = None) -> Optional[Dict[str, str]]:
        """
        Detect proxy patterns through bytecode analysis and storage slot examination.
        
        Args:
            address: Contract address to analyze
            block_number: Block number for historical analysis
            
        Returns:
            Dictionary with proxy type and implementation address if detected
        """
        try:
            bytecode = self.web3.eth.get_code(address, block_identifier=block_number or 'latest')
            
            if not bytecode or bytecode == b'0x':
                return None
            
            bytecode_hex = bytecode.hex()
            
            proxy_type = self._analyze_bytecode_patterns(bytecode_hex)
            
            if proxy_type:
                implementation = await self._get_implementation_address(address, proxy_type, block_number)
                
                if implementation and implementation != '0x' + '0' * 40:
                    return {
                        'type': proxy_type,
                        'implementation': to_checksum_address(implementation)
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error detecting proxy pattern for {address}: {e}")
            return None
    
    def _analyze_bytecode_patterns(self, bytecode: str) -> Optional[str]:
        """Analyze bytecode for known proxy patterns."""
        
        if '360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc' in bytecode:
            return 'EIP1967'
        
        if 'c5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7' in bytecode:
            return 'EIP1822'
        
        if '7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3' in bytecode:
            return 'OpenZeppelin'
        
        minimal_proxy_pattern = r'363d3d373d3d3d363d73[a-fA-F0-9]{40}5af43d82803e903d91602b57fd5bf3'
        if re.search(minimal_proxy_pattern, bytecode):
            return 'EIP1167'
        
        if 'delegatecall' in bytecode.lower() or '3660008037' in bytecode:
            return 'Custom'
        
        return None
    
    async def _get_implementation_address(self, proxy_address: str, proxy_type: str, block_number: Optional[int] = None) -> Optional[str]:
        """Get implementation address from proxy storage slots."""
        
        try:
            if proxy_type in self.PROXY_PATTERNS:
                slot = self.PROXY_PATTERNS[proxy_type]['implementation_slot']
                
                storage_value = self.web3.eth.get_storage_at(
                    proxy_address, 
                    slot, 
                    block_identifier=block_number or 'latest'
                )
                
                if storage_value and storage_value != b'\x00' * 32:
                    implementation = '0x' + storage_value[-20:].hex()
                    return implementation
            
            elif proxy_type == 'EIP1167':
                bytecode = self.web3.eth.get_code(proxy_address, block_identifier=block_number or 'latest')
                bytecode_hex = bytecode.hex()
                
                match = re.search(r'363d3d373d3d3d363d73([a-fA-F0-9]{40})5af43d82803e903d91602b57fd5bf3', bytecode_hex)
                if match:
                    return '0x' + match.group(1)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting implementation address: {e}")
            return None
    
    async def _make_request(self, url: str, params: Dict) -> Optional[Dict]:
        """Make HTTP request with retry logic."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
                
            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        return None
    
    def get_contract_functions(self, contract_info: ContractInfo) -> List[Dict[str, Any]]:
        """
        Extract all function signatures from contract ABI.
        
        Args:
            contract_info: Contract information with ABI
            
        Returns:
            List of function information dictionaries
        """
        functions = []
        
        for item in contract_info.abi:
            if item.get('type') == 'function':
                functions.append({
                    'name': item.get('name'),
                    'inputs': item.get('inputs', []),
                    'outputs': item.get('outputs', []),
                    'stateMutability': item.get('stateMutability', 'nonpayable'),
                    'signature': self._generate_function_signature(item)
                })
        
        return functions
    
    def _generate_function_signature(self, function_abi: Dict) -> str:
        """Generate function signature from ABI."""
        name = function_abi.get('name', '')
        inputs = function_abi.get('inputs', [])
        
        param_types = [param.get('type', '') for param in inputs]
        signature = f"{name}({','.join(param_types)})"
        
        return signature
    
    async def batch_fetch_contracts(self, addresses: List[str], block_number: Optional[int] = None) -> Dict[str, ContractInfo]:
        """
        Fetch multiple contracts in parallel with rate limiting.
        
        Args:
            addresses: List of contract addresses
            block_number: Historical block number
            
        Returns:
            Dictionary mapping addresses to ContractInfo objects
        """
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        
        async def fetch_single(address: str) -> Tuple[str, ContractInfo]:
            async with semaphore:
                try:
                    info = await self.fetch_contract_source(address, block_number)
                    return address, info
                except Exception as e:
                    logger.error(f"Failed to fetch contract {address}: {e}")
                    return address, None
        
        tasks = [fetch_single(addr) for addr in addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {addr: info for addr, info in results if info is not None}
