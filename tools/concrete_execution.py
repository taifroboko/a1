"""
Concrete Execution Tool - A1 Agentic System

This tool implements Forge-based blockchain simulation with deterministic testing,
enabling the agent to execute exploit strategies in controlled environments
with comprehensive execution analytics and state validation.

Based on the A1 research paper specifications.
"""

import asyncio
import subprocess
import json
import os
import tempfile
import shutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """Container for execution result information"""
    success: bool
    transaction_hash: Optional[str]
    gas_used: int
    gas_limit: int
    block_number: int
    timestamp: int
    return_data: Optional[str]
    logs: List[Dict]
    state_changes: Dict[str, Any]
    error_message: Optional[str] = None
    execution_trace: Optional[List[Dict]] = None

@dataclass
class ForgeTestResult:
    """Container for Forge test execution results"""
    test_name: str
    passed: bool
    gas_used: int
    execution_time: float
    logs: List[str]
    traces: List[Dict]
    coverage: Dict[str, float]
    assertions: List[Dict]

@dataclass
class BlockchainFork:
    """Container for blockchain fork information"""
    fork_url: str
    block_number: int
    chain_id: int
    fork_id: str
    contracts: Dict[str, str]  # address -> deployed bytecode

class ConcreteExecutionTool:
    """
    Implements Forge-based blockchain simulation and testing.
    
    Provides deterministic blockchain simulation, comprehensive execution analytics,
    and state validation for exploit strategy testing.
    """
    
    def __init__(self, ethereum_rpc_url: str, bsc_rpc_url: str, work_dir: Optional[str] = None):
        """
        Initialize the concrete execution tool.
        
        Args:
            ethereum_rpc_url: Ethereum RPC endpoint for forking
            bsc_rpc_url: BSC RPC endpoint for forking
            work_dir: Working directory for Forge projects
        """
        self.ethereum_rpc_url = ethereum_rpc_url
        self.bsc_rpc_url = bsc_rpc_url
        self.work_dir = Path(work_dir) if work_dir else Path.cwd() / "forge_workspace"
        self.work_dir.mkdir(exist_ok=True)
        
        self.active_forks: Dict[str, BlockchainFork] = {}
        
        self.forge_config = {
            "profile": "default",
            "src": "src",
            "out": "out",
            "libs": ["lib"],
            "remappings": [
                "@openzeppelin/=lib/openzeppelin-contracts/",
                "@forge-std/=lib/forge-std/src/",
                "ds-test/=lib/ds-test/src/"
            ],
            "optimizer": True,
            "optimizer_runs": 200,
            "via_ir": False,
            "verbosity": 3,
            "ffi": True,
            "fs_permissions": [{"access": "read-write", "path": "./"}]
        }
    
    async def create_blockchain_fork(self, chain: str, block_number: Optional[int] = None) -> str:
        """
        Create a blockchain fork for testing.
        
        Args:
            chain: Chain to fork ('ethereum' or 'bsc')
            block_number: Block number to fork from (None for latest)
            
        Returns:
            Fork ID for referencing the fork
        """
        logger.info(f"Creating {chain} fork at block {block_number or 'latest'}")
        
        if chain.lower() == 'ethereum':
            rpc_url = self.ethereum_rpc_url
            chain_id = 1
        elif chain.lower() == 'bsc':
            rpc_url = self.bsc_rpc_url
            chain_id = 56
        else:
            raise ValueError(f"Unsupported chain: {chain}")
        
        import time
        fork_id = f"{chain}_{int(time.time())}"
        
        fork = BlockchainFork(
            fork_url=rpc_url,
            block_number=block_number or await self._get_latest_block_number(rpc_url),
            chain_id=chain_id,
            fork_id=fork_id,
            contracts={}
        )
        
        self.active_forks[fork_id] = fork
        
        logger.info(f"Created fork {fork_id} for {chain} at block {fork.block_number}")
        return fork_id
    
    async def _get_latest_block_number(self, rpc_url: str) -> int:
        """Get the latest block number from RPC."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            
            async with session.post(rpc_url, json=payload) as response:
                data = await response.json()
                return int(data['result'], 16)
    
    async def setup_forge_project(self, project_name: str, fork_id: str) -> str:
        """
        Set up a new Forge project for testing.
        
        Args:
            project_name: Name of the project
            fork_id: Fork ID to use for testing
            
        Returns:
            Path to the created project
        """
        project_path = self.work_dir / project_name
        
        if project_path.exists():
            shutil.rmtree(project_path)
        
        await self._run_command(["forge", "init", str(project_path), "--no-git"])
        
        await self._create_foundry_config(project_path, fork_id)
        
        await self._install_forge_dependencies(project_path)
        
        logger.info(f"Set up Forge project at {project_path}")
        return str(project_path)
    
    async def _create_foundry_config(self, project_path: Path, fork_id: str):
        """Create foundry.toml configuration file."""
        fork = self.active_forks[fork_id]
        
        config_content = f"""[profile.default]
src = "src"
out = "out"
libs = ["lib"]
optimizer = true
optimizer_runs = 200
verbosity = 3
ffi = true

[rpc_endpoints]
mainnet = "{fork.fork_url}"

[etherscan]
mainnet = {{ key = "${{ETHERSCAN_API_KEY}}" }}

[fmt]
line_length = 120
tab_width = 4
bracket_spacing = true

[fuzz]
runs = 1000
max_test_rejects = 65536
seed = '0x3e8'
dictionary_weight = 40
include_storage = true
include_push_bytes = true

[invariant]
runs = 256
depth = 15
fail_on_revert = false
call_override = false
dictionary_weight = 80
include_storage = true
include_push_bytes = true
shrink_run_limit = 5000
"""
        
        config_path = project_path / "foundry.toml"
        with open(config_path, 'w') as f:
            f.write(config_content)
    
    async def _install_forge_dependencies(self, project_path: Path):
        """Install common Forge dependencies."""
        dependencies = [
            "openzeppelin-contracts",
            "forge-std"
        ]
        
        for dep in dependencies:
            await self._run_command(
                ["forge", "install", f"openzeppelin/{dep}", "--no-git"],
                cwd=project_path
            )
    
    async def deploy_contract(self, project_path: str, contract_name: str, constructor_args: List[Any], fork_id: str) -> str:
        """
        Deploy a contract to the forked blockchain.
        
        Args:
            project_path: Path to Forge project
            contract_name: Name of contract to deploy
            constructor_args: Constructor arguments
            fork_id: Fork ID to deploy to
            
        Returns:
            Deployed contract address
        """
        fork = self.active_forks[fork_id]
        
        await self._run_command(["forge", "build"], cwd=project_path)
        
        args_str = " ".join(str(arg) for arg in constructor_args) if constructor_args else ""
        
        cmd = [
            "forge", "create",
            f"src/{contract_name}.sol:{contract_name}",
            "--rpc-url", fork.fork_url,
            "--private-key", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # Anvil default key
        ]
        
        if args_str:
            cmd.extend(["--constructor-args", args_str])
        
        if fork.block_number:
            cmd.extend(["--fork-block-number", str(fork.block_number)])
        
        result = await self._run_command(cmd, cwd=project_path)
        
        address = self._extract_deployed_address(result.stdout)
        
        if address:
            fork.contracts[contract_name] = address
            logger.info(f"Deployed {contract_name} to {address}")
            return address
        else:
            raise RuntimeError(f"Failed to deploy {contract_name}: {result.stderr}")
    
    def _extract_deployed_address(self, output: str) -> Optional[str]:
        """Extract deployed contract address from forge output."""
        import re
        
        match = re.search(r'Deployed to:\s*(0x[a-fA-F0-9]{40})', output)
        if match:
            return match.group(1)
        
        return None
    
    async def execute_transaction(self, project_path: str, contract_address: str, function_signature: str, args: List[Any], fork_id: str, value: int = 0) -> ExecutionResult:
        """
        Execute a transaction on the forked blockchain.
        
        Args:
            project_path: Path to Forge project
            contract_address: Target contract address
            function_signature: Function signature to call
            args: Function arguments
            fork_id: Fork ID to execute on
            value: ETH value to send (in wei)
            
        Returns:
            ExecutionResult with execution details
        """
        fork = self.active_forks[fork_id]
        
        args_str = " ".join(str(arg) for arg in args) if args else ""
        
        cmd = [
            "cast", "send",
            contract_address,
            function_signature,
            "--rpc-url", fork.fork_url,
            "--private-key", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
            "--gas-limit", "10000000"
        ]
        
        if args_str:
            cmd.append(args_str)
        
        if value > 0:
            cmd.extend(["--value", str(value)])
        
        try:
            result = await self._run_command(cmd, cwd=project_path)
            
            tx_hash = self._extract_transaction_hash(result.stdout)
            
            if tx_hash:
                receipt = await self._get_transaction_receipt(tx_hash, fork.fork_url)
                
                return ExecutionResult(
                    success=True,
                    transaction_hash=tx_hash,
                    gas_used=receipt.get('gasUsed', 0),
                    gas_limit=receipt.get('gasLimit', 0),
                    block_number=receipt.get('blockNumber', 0),
                    timestamp=int(receipt.get('timestamp', 0)),
                    return_data=receipt.get('returnData'),
                    logs=receipt.get('logs', []),
                    state_changes={}
                )
            else:
                return ExecutionResult(
                    success=False,
                    transaction_hash=None,
                    gas_used=0,
                    gas_limit=0,
                    block_number=0,
                    timestamp=0,
                    return_data=None,
                    logs=[],
                    state_changes={},
                    error_message=result.stderr
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                transaction_hash=None,
                gas_used=0,
                gas_limit=0,
                block_number=0,
                timestamp=0,
                return_data=None,
                logs=[],
                state_changes={},
                error_message=str(e)
            )
    
    def _extract_transaction_hash(self, output: str) -> Optional[str]:
        """Extract transaction hash from cast output."""
        import re
        
        match = re.search(r'(0x[a-fA-F0-9]{64})', output)
        if match:
            return match.group(1)
        
        return None
    
    async def _get_transaction_receipt(self, tx_hash: str, rpc_url: str) -> Dict:
        """Get transaction receipt from RPC."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1
            }
            
            async with session.post(rpc_url, json=payload) as response:
                data = await response.json()
                return data.get('result', {})
    
    async def run_forge_test(self, project_path: str, test_name: Optional[str] = None, fork_id: Optional[str] = None) -> List[ForgeTestResult]:
        """
        Run Forge tests with comprehensive analytics.
        
        Args:
            project_path: Path to Forge project
            test_name: Specific test to run (None for all tests)
            fork_id: Fork ID to run tests against
            
        Returns:
            List of test results
        """
        cmd = ["forge", "test", "--json", "-vvv"]
        
        if test_name:
            cmd.extend(["--match-test", test_name])
        
        if fork_id and fork_id in self.active_forks:
            fork = self.active_forks[fork_id]
            cmd.extend(["--fork-url", fork.fork_url])
            if fork.block_number:
                cmd.extend(["--fork-block-number", str(fork.block_number)])
        
        result = await self._run_command(cmd, cwd=project_path)
        
        test_results = []
        
        try:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.startswith('{'):
                    test_data = json.loads(line)
                    
                    if test_data.get('type') == 'test_result':
                        test_result = ForgeTestResult(
                            test_name=test_data.get('name', ''),
                            passed=test_data.get('status') == 'Success',
                            gas_used=test_data.get('gas_used', 0),
                            execution_time=test_data.get('duration', 0.0),
                            logs=test_data.get('logs', []),
                            traces=test_data.get('traces', []),
                            coverage={},
                            assertions=[]
                        )
                        test_results.append(test_result)
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse test output: {e}")
            test_results = self._parse_text_test_output(result.stdout)
        
        return test_results
    
    def _parse_text_test_output(self, output: str) -> List[ForgeTestResult]:
        """Parse text-based test output as fallback."""
        test_results = []
        
        import re
        
        test_pattern = r'\[(\w+)\]\s+(\w+::\w+)\s+\(gas:\s*(\d+)\)'
        matches = re.findall(test_pattern, output)
        
        for status, test_name, gas_used in matches:
            test_result = ForgeTestResult(
                test_name=test_name,
                passed=status.upper() == 'PASS',
                gas_used=int(gas_used),
                execution_time=0.0,
                logs=[],
                traces=[],
                coverage={},
                assertions=[]
            )
            test_results.append(test_result)
        
        return test_results
    
    async def create_exploit_test(self, project_path: str, target_contract: str, exploit_strategy: Dict[str, Any]) -> str:
        """
        Create a Forge test file for exploit strategy validation.
        
        Args:
            project_path: Path to Forge project
            target_contract: Target contract address or name
            exploit_strategy: Exploit strategy details
            
        Returns:
            Path to created test file
        """
        test_content = self._generate_exploit_test_code(target_contract, exploit_strategy)
        
        test_file_path = Path(project_path) / "test" / f"Exploit_{target_contract}.t.sol"
        test_file_path.parent.mkdir(exist_ok=True)
        
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        logger.info(f"Created exploit test at {test_file_path}")
        return str(test_file_path)
    
    def _generate_exploit_test_code(self, target_contract: str, exploit_strategy: Dict[str, Any]) -> str:
        """Generate Solidity test code for exploit strategy."""
        
        test_code = f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "forge-std/console.sol";

contract Exploit_{target_contract}_Test is Test {{
    address constant TARGET_CONTRACT = {exploit_strategy.get('target_address', '0x0000000000000000000000000000000000000000')};
    address constant ATTACKER = address(0x1337);
    
    function setUp() public {{
        // Set up test environment
        vm.createFork(vm.envString("MAINNET_RPC_URL"));
        vm.rollFork({exploit_strategy.get('target_block', 'block.number')});
        
        // Fund attacker account
        vm.deal(ATTACKER, 100 ether);
        vm.startPrank(ATTACKER);
    }}
    
    function test_exploit_strategy() public {{
        // Record initial state
        uint256 initialBalance = ATTACKER.balance;
        
        console.log("Initial attacker balance:", initialBalance);
        console.log("Target contract:", TARGET_CONTRACT);
        
        // Execute exploit strategy
        {self._generate_exploit_steps(exploit_strategy)}
        
        // Verify exploit success
        uint256 finalBalance = ATTACKER.balance;
        console.log("Final attacker balance:", finalBalance);
        
        // Assert profit was made
        assertGt(finalBalance, initialBalance, "Exploit should be profitable");
        
        vm.stopPrank();
    }}
    
    function test_exploit_preconditions() public {{
        // Test that exploit preconditions are met
        {self._generate_precondition_checks(exploit_strategy)}
    }}
    
    function test_exploit_impact() public {{
        // Measure exploit impact
        {self._generate_impact_measurement(exploit_strategy)}
    }}
}}
'''
        
        return test_code
    
    def _generate_exploit_steps(self, exploit_strategy: Dict[str, Any]) -> str:
        """Generate Solidity code for exploit execution steps."""
        steps = exploit_strategy.get('steps', [])
        
        code_lines = []
        for i, step in enumerate(steps):
            step_type = step.get('type', 'call')
            
            if step_type == 'call':
                code_lines.append(f'''
        // Step {i + 1}: {step.get('description', 'Execute function call')}
        (bool success{i}, bytes memory data{i}) = TARGET_CONTRACT.call(
            abi.encodeWithSignature("{step.get('function', 'transfer(address,uint256)')}", {step.get('args', 'ATTACKER, 1000')})
        );
        require(success{i}, "Step {i + 1} failed");
        console.log("Step {i + 1} completed successfully");
''')
            
            elif step_type == 'transfer':
                code_lines.append(f'''
        // Step {i + 1}: Transfer tokens
        payable({step.get('to', 'ATTACKER')}).transfer({step.get('amount', '1 ether')});
        console.log("Transferred", {step.get('amount', '1 ether')}, "to", {step.get('to', 'ATTACKER')});
''')
        
        return '\n'.join(code_lines) if code_lines else '// No exploit steps defined'
    
    def _generate_precondition_checks(self, exploit_strategy: Dict[str, Any]) -> str:
        """Generate precondition checks for exploit."""
        preconditions = exploit_strategy.get('preconditions', [])
        
        code_lines = []
        for condition in preconditions:
            if condition.get('type') == 'balance_check':
                code_lines.append(f'''
        uint256 contractBalance = TARGET_CONTRACT.balance;
        assertGt(contractBalance, {condition.get('min_balance', '0')}, "{condition.get('description', 'Contract should have sufficient balance')}");
''')
            
            elif condition.get('type') == 'state_check':
                code_lines.append(f'''
        // Check contract state: {condition.get('description', 'State validation')}
        (bool success, bytes memory data) = TARGET_CONTRACT.call(
            abi.encodeWithSignature("{condition.get('function', 'paused()')}")
        );
        require(success, "State check failed");
''')
        
        return '\n'.join(code_lines) if code_lines else '// No preconditions defined'
    
    def _generate_impact_measurement(self, exploit_strategy: Dict[str, Any]) -> str:
        """Generate impact measurement code."""
        return '''
        // Measure various impact metrics
        uint256 contractBalanceBefore = TARGET_CONTRACT.balance;
        uint256 totalSupplyBefore = IERC20(TARGET_CONTRACT).totalSupply();
        
        // Execute exploit (simplified)
        // ... exploit code here ...
        
        uint256 contractBalanceAfter = TARGET_CONTRACT.balance;
        uint256 totalSupplyAfter = IERC20(TARGET_CONTRACT).totalSupply();
        
        console.log("Contract balance change:", contractBalanceBefore - contractBalanceAfter);
        console.log("Total supply change:", totalSupplyBefore - totalSupplyAfter);
'''
    
    async def analyze_execution_trace(self, tx_hash: str, fork_id: str) -> Dict[str, Any]:
        """
        Analyze execution trace for a transaction.
        
        Args:
            tx_hash: Transaction hash to analyze
            fork_id: Fork ID where transaction was executed
            
        Returns:
            Detailed execution trace analysis
        """
        fork = self.active_forks[fork_id]
        
        cmd = [
            "cast", "run",
            tx_hash,
            "--rpc-url", fork.fork_url,
            "--trace"
        ]
        
        result = await self._run_command(cmd)
        
        trace_analysis = {
            'transaction_hash': tx_hash,
            'gas_usage': {},
            'function_calls': [],
            'state_changes': [],
            'events': [],
            'reverts': []
        }
        
        lines = result.stdout.split('\n')
        for line in lines:
            if 'CALL' in line:
                trace_analysis['function_calls'].append(line.strip())
            elif 'SSTORE' in line:
                trace_analysis['state_changes'].append(line.strip())
            elif 'LOG' in line:
                trace_analysis['events'].append(line.strip())
            elif 'REVERT' in line:
                trace_analysis['reverts'].append(line.strip())
        
        return trace_analysis
    
    async def simulate_block_progression(self, fork_id: str, num_blocks: int) -> List[Dict[str, Any]]:
        """
        Simulate progression of multiple blocks.
        
        Args:
            fork_id: Fork ID to simulate on
            num_blocks: Number of blocks to simulate
            
        Returns:
            List of block information
        """
        fork = self.active_forks[fork_id]
        blocks = []
        
        for i in range(num_blocks):
            cmd = [
                "cast", "rpc",
                "evm_mine",
                "--rpc-url", fork.fork_url
            ]
            
            await self._run_command(cmd)
            
            block_info = await self._get_latest_block_info(fork.fork_url)
            blocks.append(block_info)
            
            await asyncio.sleep(0.1)
        
        return blocks
    
    async def _get_latest_block_info(self, rpc_url: str) -> Dict[str, Any]:
        """Get latest block information."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": ["latest", False],
                "id": 1
            }
            
            async with session.post(rpc_url, json=payload) as response:
                data = await response.json()
                return data.get('result', {})
    
    async def cleanup_fork(self, fork_id: str):
        """Clean up a blockchain fork."""
        if fork_id in self.active_forks:
            del self.active_forks[fork_id]
            logger.info(f"Cleaned up fork {fork_id}")
    
    async def _run_command(self, cmd: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run a shell command asynchronously."""
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        stdout, stderr = await process.communicate()
        
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout=stdout.decode('utf-8'),
            stderr=stderr.decode('utf-8')
        )
        
        if result.returncode != 0:
            logger.warning(f"Command failed: {' '.join(cmd)}")
            logger.warning(f"Error: {result.stderr}")
        
        return result
    
    def get_forge_project_template(self) -> str:
        """Get a template for a basic Forge project structure."""
        return '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "forge-std/console.sol";

contract ExploitTest is Test {
    function setUp() public {
        // Set up test environment
    }
    
    function testExploit() public {
        // Implement exploit test
    }
}
'''
    
    async def validate_exploit_profitability(self, execution_results: List[ExecutionResult], initial_balance: int) -> Dict[str, Any]:
        """
        Validate that an exploit strategy is profitable.
        
        Args:
            execution_results: List of execution results from exploit
            initial_balance: Initial balance before exploit
            
        Returns:
            Profitability analysis
        """
        total_gas_cost = sum(result.gas_used for result in execution_results)
        
        final_balance = initial_balance  # Placeholder
        
        profit = final_balance - initial_balance - total_gas_cost
        
        return {
            'profitable': profit > 0,
            'profit_amount': profit,
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_gas_cost': total_gas_cost,
            'roi_percentage': (profit / max(initial_balance, 1)) * 100,
            'execution_count': len(execution_results),
            'success_rate': sum(1 for r in execution_results if r.success) / max(len(execution_results), 1)
        }


# Backwards compatibility alias
ConcreteExecution = ConcreteExecutionTool
