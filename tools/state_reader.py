"""
Blockchain State Reader Tool - A1 Agentic System

This tool performs ABI analysis to identify all public and external view functions,
enabling the agent to capture contract state snapshots at target blocks through 
batch calls for comprehensive state understanding.

Based on the A1 research paper specifications.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from web3 import Web3
from web3.contract import Contract
from eth_utils import to_checksum_address, function_signature_to_4byte_selector
from eth_abi import encode, decode
import logging

logger = logging.getLogger(__name__)

@dataclass
class StateSnapshot:
    """Container for contract state snapshot"""
    contract_address: str
    block_number: int
    timestamp: int
    state_data: Dict[str, Any]
    view_functions: List[str]
    storage_slots: Dict[str, str]
    balance: int

@dataclass
class FunctionCall:
    """Container for function call information"""
    function_name: str
    function_signature: str
    inputs: List[Dict]
    outputs: List[Dict]
    result: Any
    success: bool
    error: Optional[str] = None

class BlockchainStateReader:
    """
    Reads and analyzes blockchain state for smart contracts.
    
    Performs comprehensive state analysis including view function calls,
    storage slot reading, and balance tracking at specific block numbers.
    """
    
    def __init__(self, web3_client: Web3):
        """
        Initialize the state reader.
        
        Args:
            web3_client: Web3 instance for blockchain interaction
        """
        self.web3 = web3_client
        
        self.STANDARD_STORAGE_SLOTS = {
            'owner': '0x0',  # Ownable contracts often store owner at slot 0
            'paused': '0x1',  # Pausable contracts
            'total_supply': '0x2',  # ERC20 total supply
            'name': '0x3',  # ERC20 name
            'symbol': '0x4',  # ERC20 symbol
            'decimals': '0x5',  # ERC20 decimals
        }
    
    async def capture_state_snapshot(self, contract_address: str, contract_abi: List[Dict], block_number: Optional[int] = None) -> StateSnapshot:
        """
        Capture comprehensive state snapshot of a contract.
        
        Args:
            contract_address: Contract address to analyze
            contract_abi: Contract ABI for function analysis
            block_number: Block number for historical state (None for latest)
            
        Returns:
            StateSnapshot object with complete state information
        """
        contract_address = to_checksum_address(contract_address)
        block_identifier = block_number or 'latest'
        
        logger.info(f"Capturing state snapshot for {contract_address} at block {block_identifier}")
        
        if block_number:
            block_info = self.web3.eth.get_block(block_number)
            timestamp = block_info.timestamp
        else:
            block_info = self.web3.eth.get_block('latest')
            timestamp = block_info.timestamp
            block_number = block_info.number
        
        balance = self.web3.eth.get_balance(contract_address, block_identifier)
        
        view_functions = self._extract_view_functions(contract_abi)
        
        state_data = await self._execute_view_functions(
            contract_address, 
            contract_abi, 
            view_functions, 
            block_identifier
        )
        
        storage_slots = await self._read_storage_slots(contract_address, block_identifier)
        
        return StateSnapshot(
            contract_address=contract_address,
            block_number=block_number,
            timestamp=timestamp,
            state_data=state_data,
            view_functions=[f['signature'] for f in view_functions],
            storage_slots=storage_slots,
            balance=balance
        )
    
    def _extract_view_functions(self, contract_abi: List[Dict]) -> List[Dict]:
        """
        Extract all view and pure functions from contract ABI.
        
        Args:
            contract_abi: Contract ABI
            
        Returns:
            List of view function definitions
        """
        view_functions = []
        
        for item in contract_abi:
            if (item.get('type') == 'function' and 
                item.get('stateMutability') in ['view', 'pure'] and
                len(item.get('inputs', [])) == 0):  # Only no-parameter functions for safety
                
                signature = self._generate_function_signature(item)
                
                view_functions.append({
                    'name': item.get('name'),
                    'signature': signature,
                    'inputs': item.get('inputs', []),
                    'outputs': item.get('outputs', []),
                    'stateMutability': item.get('stateMutability')
                })
        
        return view_functions
    
    def _generate_function_signature(self, function_abi: Dict) -> str:
        """Generate function signature from ABI."""
        name = function_abi.get('name', '')
        inputs = function_abi.get('inputs', [])
        
        param_types = [param.get('type', '') for param in inputs]
        signature = f"{name}({','.join(param_types)})"
        
        return signature
    
    async def _execute_view_functions(self, contract_address: str, contract_abi: List[Dict], view_functions: List[Dict], block_identifier: Union[int, str]) -> Dict[str, Any]:
        """
        Execute all view functions and collect results.
        
        Args:
            contract_address: Contract address
            contract_abi: Contract ABI
            view_functions: List of view functions to call
            block_identifier: Block number or 'latest'
            
        Returns:
            Dictionary mapping function names to results
        """
        contract = self.web3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )
        
        state_data = {}
        
        batch_size = 10
        for i in range(0, len(view_functions), batch_size):
            batch = view_functions[i:i + batch_size]
            
            tasks = []
            for func_info in batch:
                task = self._call_view_function(contract, func_info, block_identifier)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for func_info, result in zip(batch, results):
                func_name = func_info['name']
                
                if isinstance(result, Exception):
                    state_data[func_name] = {
                        'success': False,
                        'error': str(result),
                        'value': None
                    }
                else:
                    state_data[func_name] = result
            
            await asyncio.sleep(0.1)
        
        return state_data
    
    async def _call_view_function(self, contract: Contract, func_info: Dict, block_identifier: Union[int, str]) -> Dict[str, Any]:
        """
        Call a single view function and return formatted result.
        
        Args:
            contract: Web3 contract instance
            func_info: Function information
            block_identifier: Block number or 'latest'
            
        Returns:
            Dictionary with function call result
        """
        try:
            func_name = func_info['name']
            
            if hasattr(contract.functions, func_name):
                func = getattr(contract.functions, func_name)
                
                result = func().call(block_identifier=block_identifier)
                
                formatted_result = self._format_function_result(result, func_info['outputs'])
                
                return {
                    'success': True,
                    'value': formatted_result,
                    'raw_value': result,
                    'signature': func_info['signature']
                }
            else:
                return {
                    'success': False,
                    'error': f"Function {func_name} not found in contract",
                    'value': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'value': None
            }
    
    def _format_function_result(self, result: Any, output_types: List[Dict]) -> Any:
        """Format function result for readability."""
        try:
            if len(output_types) == 0:
                return None
            elif len(output_types) == 1:
                return self._format_single_value(result, output_types[0]['type'])
            else:
                formatted = {}
                for i, output in enumerate(output_types):
                    key = output.get('name', f'output_{i}')
                    value = result[i] if isinstance(result, (list, tuple)) else result
                    formatted[key] = self._format_single_value(value, output['type'])
                return formatted
                
        except Exception as e:
            logger.warning(f"Error formatting function result: {e}")
            return result
    
    def _format_single_value(self, value: Any, value_type: str) -> Any:
        """Format a single value based on its type."""
        try:
            if value_type.startswith('address'):
                if isinstance(value, (list, tuple)):
                    return [to_checksum_address(addr) for addr in value]
                else:
                    return to_checksum_address(value)
            
            elif value_type.startswith('uint') or value_type.startswith('int'):
                if isinstance(value, (list, tuple)):
                    return [str(v) for v in value]
                else:
                    return str(value)
            
            elif value_type.startswith('bytes'):
                if isinstance(value, bytes):
                    return '0x' + value.hex()
                return str(value)
            
            elif value_type == 'string':
                return str(value)
            
            elif value_type == 'bool':
                return bool(value)
            
            else:
                return str(value)
                
        except Exception as e:
            logger.warning(f"Error formatting value {value} of type {value_type}: {e}")
            return str(value)
    
    async def _read_storage_slots(self, contract_address: str, block_identifier: Union[int, str]) -> Dict[str, str]:
        """
        Read important storage slots from the contract.
        
        Args:
            contract_address: Contract address
            block_identifier: Block number or 'latest'
            
        Returns:
            Dictionary mapping slot names to values
        """
        storage_data = {}
        
        for slot_name, slot_hex in self.STANDARD_STORAGE_SLOTS.items():
            try:
                storage_value = self.web3.eth.get_storage_at(
                    contract_address,
                    slot_hex,
                    block_identifier
                )
                
                if storage_value and storage_value != b'\x00' * 32:
                    storage_data[slot_name] = '0x' + storage_value.hex()
                
            except Exception as e:
                logger.warning(f"Error reading storage slot {slot_name}: {e}")
        
        for i in range(10):
            try:
                slot_hex = f'0x{i:x}'
                storage_value = self.web3.eth.get_storage_at(
                    contract_address,
                    slot_hex,
                    block_identifier
                )
                
                if storage_value and storage_value != b'\x00' * 32:
                    storage_data[f'slot_{i}'] = '0x' + storage_value.hex()
                    
            except Exception as e:
                logger.warning(f"Error reading storage slot {i}: {e}")
        
        return storage_data
    
    async def compare_state_snapshots(self, snapshot1: StateSnapshot, snapshot2: StateSnapshot) -> Dict[str, Any]:
        """
        Compare two state snapshots to identify changes.
        
        Args:
            snapshot1: First snapshot (earlier)
            snapshot2: Second snapshot (later)
            
        Returns:
            Dictionary with comparison results
        """
        comparison = {
            'contract_address': snapshot1.contract_address,
            'block_range': f"{snapshot1.block_number} -> {snapshot2.block_number}",
            'time_range': f"{snapshot1.timestamp} -> {snapshot2.timestamp}",
            'balance_change': snapshot2.balance - snapshot1.balance,
            'function_changes': {},
            'storage_changes': {},
            'new_functions': [],
            'removed_functions': []
        }
        
        all_functions = set(snapshot1.state_data.keys()) | set(snapshot2.state_data.keys())
        
        for func_name in all_functions:
            if func_name in snapshot1.state_data and func_name in snapshot2.state_data:
                old_value = snapshot1.state_data[func_name].get('value')
                new_value = snapshot2.state_data[func_name].get('value')
                
                if old_value != new_value:
                    comparison['function_changes'][func_name] = {
                        'old_value': old_value,
                        'new_value': new_value
                    }
            elif func_name in snapshot2.state_data:
                comparison['new_functions'].append(func_name)
            else:
                comparison['removed_functions'].append(func_name)
        
        all_slots = set(snapshot1.storage_slots.keys()) | set(snapshot2.storage_slots.keys())
        
        for slot_name in all_slots:
            if slot_name in snapshot1.storage_slots and slot_name in snapshot2.storage_slots:
                old_value = snapshot1.storage_slots[slot_name]
                new_value = snapshot2.storage_slots[slot_name]
                
                if old_value != new_value:
                    comparison['storage_changes'][slot_name] = {
                        'old_value': old_value,
                        'new_value': new_value
                    }
        
        return comparison
    
    async def analyze_state_patterns(self, snapshots: List[StateSnapshot]) -> Dict[str, Any]:
        """
        Analyze patterns across multiple state snapshots.
        
        Args:
            snapshots: List of state snapshots in chronological order
            
        Returns:
            Dictionary with pattern analysis
        """
        if len(snapshots) < 2:
            return {'error': 'Need at least 2 snapshots for pattern analysis'}
        
        analysis = {
            'contract_address': snapshots[0].contract_address,
            'snapshot_count': len(snapshots),
            'time_span': snapshots[-1].timestamp - snapshots[0].timestamp,
            'block_span': snapshots[-1].block_number - snapshots[0].block_number,
            'balance_trend': [],
            'function_volatility': {},
            'storage_volatility': {},
            'state_stability': {}
        }
        
        for snapshot in snapshots:
            analysis['balance_trend'].append({
                'block': snapshot.block_number,
                'balance': snapshot.balance,
                'timestamp': snapshot.timestamp
            })
        
        all_functions = set()
        for snapshot in snapshots:
            all_functions.update(snapshot.state_data.keys())
        
        for func_name in all_functions:
            values = []
            for snapshot in snapshots:
                if func_name in snapshot.state_data:
                    value = snapshot.state_data[func_name].get('value')
                    values.append(value)
            
            unique_values = len(set(str(v) for v in values))
            analysis['function_volatility'][func_name] = {
                'unique_values': unique_values,
                'total_snapshots': len(values),
                'stability_ratio': 1.0 - (unique_values - 1) / max(len(values) - 1, 1)
            }
        
        total_functions = len(all_functions)
        stable_functions = sum(1 for v in analysis['function_volatility'].values() if v['stability_ratio'] > 0.8)
        
        analysis['state_stability'] = {
            'stable_function_ratio': stable_functions / max(total_functions, 1),
            'overall_stability': 'high' if stable_functions / max(total_functions, 1) > 0.8 else 'medium' if stable_functions / max(total_functions, 1) > 0.5 else 'low'
        }
        
        return analysis
    
    async def batch_capture_snapshots(self, contracts: List[Tuple[str, List[Dict]]], block_number: Optional[int] = None) -> Dict[str, StateSnapshot]:
        """
        Capture state snapshots for multiple contracts in parallel.
        
        Args:
            contracts: List of (address, abi) tuples
            block_number: Block number for historical state
            
        Returns:
            Dictionary mapping addresses to StateSnapshot objects
        """
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        
        async def capture_single(address: str, abi: List[Dict]) -> Tuple[str, StateSnapshot]:
            async with semaphore:
                try:
                    snapshot = await self.capture_state_snapshot(address, abi, block_number)
                    return address, snapshot
                except Exception as e:
                    logger.error(f"Failed to capture snapshot for {address}: {e}")
                    return address, None
        
        tasks = [capture_single(addr, abi) for addr, abi in contracts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {addr: snapshot for addr, snapshot in results if snapshot is not None}
    
    def extract_critical_state_variables(self, snapshot: StateSnapshot) -> Dict[str, Any]:
        """
        Extract critical state variables that are commonly targeted in exploits.
        
        Args:
            snapshot: State snapshot to analyze
            
        Returns:
            Dictionary with critical state variables
        """
        critical_vars = {
            'balances': {},
            'allowances': {},
            'ownership': {},
            'paused_state': None,
            'total_supply': None,
            'reserves': {},
            'fees': {},
            'timestamps': {}
        }
        
        for func_name, func_data in snapshot.state_data.items():
            if not func_data.get('success'):
                continue
                
            value = func_data.get('value')
            func_name_lower = func_name.lower()
            
            if 'balance' in func_name_lower:
                critical_vars['balances'][func_name] = value
            
            elif 'supply' in func_name_lower:
                critical_vars['total_supply'] = value
            
            elif any(keyword in func_name_lower for keyword in ['owner', 'admin', 'governance']):
                critical_vars['ownership'][func_name] = value
            
            elif 'paused' in func_name_lower:
                critical_vars['paused_state'] = value
            
            elif 'reserve' in func_name_lower:
                critical_vars['reserves'][func_name] = value
            
            elif 'fee' in func_name_lower:
                critical_vars['fees'][func_name] = value
            
            elif any(keyword in func_name_lower for keyword in ['time', 'timestamp', 'deadline']):
                critical_vars['timestamps'][func_name] = value
        
        return critical_vars
