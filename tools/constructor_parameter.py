"""
Constructor Parameter Tool - A1 Agentic System

This tool analyzes deployment transaction calldata to reconstruct initialization 
parameters, providing the agent with configuration context including token addresses,
fee specifications, and access control parameters.

Based on the A1 research paper specifications.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from web3 import Web3
from eth_abi import decode
from eth_utils import to_checksum_address, keccak
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConstructorParameter:
    """Container for a single constructor parameter"""
    name: str
    type: str
    value: Any
    decoded_value: Optional[str] = None

@dataclass
class ConstructorInfo:
    """Container for complete constructor information"""
    contract_address: str
    deployer_address: str
    deployment_tx_hash: str
    block_number: int
    parameters: List[ConstructorParameter]
    creation_code: str
    runtime_code: str
    gas_used: int

class ConstructorParameterTool:
    """
    Analyzes deployment transactions to extract constructor parameters.
    
    Reconstructs initialization parameters from deployment transaction calldata,
    providing context about contract configuration and initial state.
    """
    
    def __init__(self, web3_client: Web3, etherscan_api_key: str, bscscan_api_key: str):
        """
        Initialize the constructor parameter tool.
        
        Args:
            web3_client: Web3 instance for blockchain interaction
            etherscan_api_key: Etherscan API key for transaction data
            bscscan_api_key: BSCscan API key for transaction data
        """
        self.web3 = web3_client
        self.etherscan_api_key = etherscan_api_key
        self.bscscan_api_key = bscscan_api_key
        
        self.scanner_url = "https://api.etherscan.io/api"
        self.api_key = etherscan_api_key
        self.chain_id = None
    
    async def analyze_constructor_parameters(self, contract_address: str, contract_abi: List[Dict]) -> ConstructorInfo:
        """
        Analyze constructor parameters from deployment transaction.
        
        Args:
            contract_address: Address of the deployed contract
            contract_abi: Contract ABI containing constructor definition
            
        Returns:
            ConstructorInfo object with decoded parameters
        """
        contract_address = to_checksum_address(contract_address)
        logger.info(f"Analyzing constructor parameters for: {contract_address}")
        
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
        
        deployment_tx = await self._find_deployment_transaction(contract_address)
        
        if not deployment_tx:
            raise ValueError(f"Could not find deployment transaction for {contract_address}")
        
        constructor_abi = self._extract_constructor_abi(contract_abi)
        
        parameters = []
        if constructor_abi and deployment_tx.get('input'):
            parameters = await self._decode_constructor_parameters(
                deployment_tx['input'], 
                constructor_abi,
                deployment_tx.get('contractAddress', contract_address)
            )
        
        receipt = self.web3.eth.get_transaction_receipt(deployment_tx['hash'])
        
        return ConstructorInfo(
            contract_address=contract_address,
            deployer_address=to_checksum_address(deployment_tx['from']),
            deployment_tx_hash=deployment_tx['hash'],
            block_number=int(deployment_tx['blockNumber'], 16) if isinstance(deployment_tx['blockNumber'], str) else deployment_tx['blockNumber'],
            parameters=parameters,
            creation_code=deployment_tx.get('input', ''),
            runtime_code=self.web3.eth.get_code(contract_address).hex(),
            gas_used=receipt.gasUsed
        )
    
    async def _find_deployment_transaction(self, contract_address: str) -> Optional[Dict]:
        """Find the deployment transaction for a contract."""
        try:
            creation_tx = await self._get_contract_creation_tx(contract_address)
            if creation_tx:
                return creation_tx
            
            return await self._search_deployment_in_blocks(contract_address)
            
        except Exception as e:
            logger.error(f"Error finding deployment transaction: {e}")
            return None
    
    async def _get_contract_creation_tx(self, contract_address: str) -> Optional[Dict]:
        """Get contract creation transaction from scanner API."""
        import requests
        
        params = {
            'module': 'contract',
            'action': 'getcontractcreation',
            'contractaddresses': contract_address,
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(self.scanner_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1' and data.get('result'):
                result = data['result'][0]
                
                tx_hash = result.get('txHash')
                if tx_hash:
                    tx = self.web3.eth.get_transaction(tx_hash)
                    return dict(tx)
            
        except Exception as e:
            logger.warning(f"Scanner API failed: {e}")
        
        return None
    
    async def _search_deployment_in_blocks(self, contract_address: str, max_blocks: int = 1000) -> Optional[Dict]:
        """Search for deployment transaction in recent blocks."""
        try:
            current_block = self.web3.eth.block_number
            
            for block_num in range(current_block, max(0, current_block - max_blocks), -1):
                block = self.web3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    if tx.to is None:  # Contract creation transaction
                        receipt = self.web3.eth.get_transaction_receipt(tx.hash)
                        if receipt.contractAddress and receipt.contractAddress.lower() == contract_address.lower():
                            return dict(tx)
            
        except Exception as e:
            logger.warning(f"Block search failed: {e}")
        
        return None
    
    def _extract_constructor_abi(self, contract_abi: List[Dict]) -> Optional[Dict]:
        """Extract constructor ABI from contract ABI."""
        for item in contract_abi:
            if item.get('type') == 'constructor':
                return item
        return None
    
    async def _decode_constructor_parameters(self, input_data: str, constructor_abi: Dict, contract_address: str) -> List[ConstructorParameter]:
        """
        Decode constructor parameters from transaction input data.
        
        Args:
            input_data: Transaction input data (creation code + constructor args)
            constructor_abi: Constructor ABI definition
            contract_address: Address of deployed contract
            
        Returns:
            List of decoded constructor parameters
        """
        parameters = []
        
        try:
            runtime_code = self.web3.eth.get_code(contract_address).hex()
            
            if not runtime_code or runtime_code == '0x':
                logger.warning("No runtime code found for contract")
                return parameters
            
            input_data = input_data[2:] if input_data.startswith('0x') else input_data
            runtime_code = runtime_code[2:] if runtime_code.startswith('0x') else runtime_code
            
            constructor_args_start = self._find_constructor_args_start(input_data, runtime_code)
            
            if constructor_args_start == -1:
                logger.warning("Could not locate constructor arguments in input data")
                return parameters
            
            constructor_args_hex = input_data[constructor_args_start:]
            
            if not constructor_args_hex:
                logger.info("No constructor arguments found")
                return parameters
            
            param_types = [param['type'] for param in constructor_abi.get('inputs', [])]
            param_names = [param['name'] for param in constructor_abi.get('inputs', [])]
            
            if param_types:
                constructor_args_bytes = bytes.fromhex(constructor_args_hex)
                decoded_values = decode(param_types, constructor_args_bytes)
                
                for i, (name, param_type, value) in enumerate(zip(param_names, param_types, decoded_values)):
                    decoded_value = await self._format_parameter_value(value, param_type)
                    
                    parameters.append(ConstructorParameter(
                        name=name or f"param_{i}",
                        type=param_type,
                        value=value,
                        decoded_value=decoded_value
                    ))
            
        except Exception as e:
            logger.error(f"Error decoding constructor parameters: {e}")
        
        return parameters
    
    def _find_constructor_args_start(self, input_data: str, runtime_code: str) -> int:
        """
        Find where constructor arguments start in the input data.
        
        This is a heuristic approach that looks for patterns in the bytecode.
        """
        try:
            runtime_code_pos = input_data.find(runtime_code)
            if runtime_code_pos != -1:
                return runtime_code_pos + len(runtime_code)
            
            constructor_end_patterns = [
                'f3',  # RETURN opcode
                '5b',  # JUMPDEST opcode
                '00',  # STOP opcode
            ]
            
            for pattern in constructor_end_patterns:
                pattern_pos = input_data.rfind(pattern)
                if pattern_pos != -1:
                    remaining_length = len(input_data) - (pattern_pos + len(pattern))
                    if remaining_length > 0 and remaining_length % 64 == 0:  # Constructor args are 32-byte aligned
                        return pattern_pos + len(pattern)
            
            if len(input_data) > 48000:  # 24KB * 2 (hex chars)
                return 48000
            
            return -1
            
        except Exception as e:
            logger.warning(f"Error finding constructor args start: {e}")
            return -1
    
    async def _format_parameter_value(self, value: Any, param_type: str) -> str:
        """Format parameter value for human readability."""
        try:
            if param_type.startswith('address'):
                if isinstance(value, (list, tuple)):
                    return [to_checksum_address(addr) for addr in value]
                else:
                    return to_checksum_address(value)
            
            elif param_type.startswith('uint') or param_type.startswith('int'):
                if isinstance(value, (list, tuple)):
                    return [str(v) for v in value]
                else:
                    return str(value)
            
            elif param_type.startswith('bytes'):
                if isinstance(value, bytes):
                    try:
                        decoded = value.decode('utf-8').rstrip('\x00')
                        if decoded.isprintable():
                            return f'"{decoded}"'
                    except:
                        pass
                    return '0x' + value.hex()
                return str(value)
            
            elif param_type == 'string':
                return f'"{value}"'
            
            elif param_type == 'bool':
                return str(value).lower()
            
            else:
                return str(value)
                
        except Exception as e:
            logger.warning(f"Error formatting parameter value: {e}")
            return str(value)
    
    def analyze_parameter_significance(self, constructor_info: ConstructorInfo) -> Dict[str, Any]:
        """
        Analyze the significance of constructor parameters for exploit generation.
        
        Args:
            constructor_info: Constructor information to analyze
            
        Returns:
            Dictionary with parameter analysis and security implications
        """
        analysis = {
            'critical_parameters': [],
            'token_addresses': [],
            'access_control': [],
            'fee_parameters': [],
            'time_parameters': [],
            'security_implications': []
        }
        
        for param in constructor_info.parameters:
            param_analysis = self._analyze_single_parameter(param)
            
            if param_analysis['is_critical']:
                analysis['critical_parameters'].append({
                    'name': param.name,
                    'type': param.type,
                    'value': param.decoded_value,
                    'significance': param_analysis['significance']
                })
            
            if param_analysis['category'] == 'token_address':
                analysis['token_addresses'].append(param.decoded_value)
            elif param_analysis['category'] == 'access_control':
                analysis['access_control'].append({
                    'parameter': param.name,
                    'address': param.decoded_value
                })
            elif param_analysis['category'] == 'fee':
                analysis['fee_parameters'].append({
                    'parameter': param.name,
                    'value': param.decoded_value
                })
            elif param_analysis['category'] == 'time':
                analysis['time_parameters'].append({
                    'parameter': param.name,
                    'value': param.decoded_value
                })
        
        analysis['security_implications'] = self._generate_security_implications(constructor_info)
        
        return analysis
    
    def _analyze_single_parameter(self, param: ConstructorParameter) -> Dict[str, Any]:
        """Analyze a single constructor parameter for security significance."""
        analysis = {
            'is_critical': False,
            'category': 'other',
            'significance': ''
        }
        
        param_name_lower = param.name.lower()
        
        if param.type == 'address' and any(keyword in param_name_lower for keyword in ['token', 'asset', 'coin', 'currency']):
            analysis['is_critical'] = True
            analysis['category'] = 'token_address'
            analysis['significance'] = 'Token address used in contract operations'
        
        elif param.type == 'address' and any(keyword in param_name_lower for keyword in ['owner', 'admin', 'manager', 'controller', 'governance']):
            analysis['is_critical'] = True
            analysis['category'] = 'access_control'
            analysis['significance'] = 'Administrative address with special privileges'
        
        elif any(keyword in param_name_lower for keyword in ['fee', 'rate', 'percentage', 'basis', 'commission']):
            analysis['is_critical'] = True
            analysis['category'] = 'fee'
            analysis['significance'] = 'Fee parameter affecting economic calculations'
        
        elif any(keyword in param_name_lower for keyword in ['time', 'duration', 'period', 'deadline', 'timestamp']):
            analysis['is_critical'] = True
            analysis['category'] = 'time'
            analysis['significance'] = 'Time-based parameter affecting contract behavior'
        
        elif any(keyword in param_name_lower for keyword in ['supply', 'amount', 'balance', 'limit', 'cap']):
            analysis['is_critical'] = True
            analysis['category'] = 'economic'
            analysis['significance'] = 'Economic parameter affecting token/value calculations'
        
        return analysis
    
    def _generate_security_implications(self, constructor_info: ConstructorInfo) -> List[str]:
        """Generate security implications based on constructor parameters."""
        implications = []
        
        for param in constructor_info.parameters:
            param_name_lower = param.name.lower()
            
            if param.type == 'address' and 'owner' in param_name_lower:
                implications.append("Owner address set in constructor - check for proper access control")
            
            if 'fee' in param_name_lower and param.type.startswith('uint'):
                implications.append("Fee parameter in constructor - verify fee calculation logic for overflow/underflow")
            
            if param.type == 'address' and any(keyword in param_name_lower for keyword in ['token', 'asset']):
                implications.append("Token address in constructor - verify token contract interactions")
            
            if 'time' in param_name_lower or 'duration' in param_name_lower:
                implications.append("Time-based parameter - check for timestamp manipulation vulnerabilities")
        
        return implications
    
    async def batch_analyze_constructors(self, contracts: List[Tuple[str, List[Dict]]]) -> Dict[str, ConstructorInfo]:
        """
        Analyze constructor parameters for multiple contracts in parallel.
        
        Args:
            contracts: List of (address, abi) tuples
            
        Returns:
            Dictionary mapping addresses to ConstructorInfo objects
        """
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests
        
        async def analyze_single(address: str, abi: List[Dict]) -> Tuple[str, ConstructorInfo]:
            async with semaphore:
                try:
                    info = await self.analyze_constructor_parameters(address, abi)
                    return address, info
                except Exception as e:
                    logger.error(f"Failed to analyze constructor for {address}: {e}")
                    return address, None
        
        tasks = [analyze_single(addr, abi) for addr, abi in contracts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {addr: info for addr, info in results if info is not None}
