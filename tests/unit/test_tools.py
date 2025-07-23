"""
Unit Tests - Domain-Specific Tools

Test all 6 domain-specific tools for the A1 system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from tools.source_code_fetcher import SourceCodeFetcher
from tools.constructor_parameter import ConstructorParameter
from tools.state_reader import StateReader
from tools.code_sanitizer import CodeSanitizer
from tools.concrete_execution import ConcreteExecution
from tools.revenue_normalizer import RevenueNormalizer

class TestSourceCodeFetcher:
    """Test cases for SourceCodeFetcher."""
    
    @pytest.fixture
    def fetcher(self, test_config, mock_blockchain_client):
        """Create source code fetcher instance."""
        return SourceCodeFetcher(test_config, mock_blockchain_client)
    
    @pytest.mark.asyncio
    async def test_fetch_contract_source(self, fetcher, sample_contract_address):
        """Test fetching contract source code."""
        result = await fetcher.fetch_contract_source(sample_contract_address, 'ethereum')
        
        assert result['success']
        assert 'source_code' in result
        assert 'abi' in result
        assert 'compiler_version' in result
    
    @pytest.mark.asyncio
    async def test_fetch_invalid_contract(self, fetcher):
        """Test fetching invalid contract address."""
        result = await fetcher.fetch_contract_source('0xinvalid', 'ethereum')
        
        assert not result['success']
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_analyze_source_complexity(self, fetcher, sample_solidity_code):
        """Test source code complexity analysis."""
        analysis = await fetcher.analyze_source_complexity(sample_solidity_code)
        
        assert 'function_count' in analysis
        assert 'line_count' in analysis
        assert 'complexity_score' in analysis
        assert analysis['function_count'] >= 0

class TestConstructorParameter:
    """Test cases for ConstructorParameter."""
    
    @pytest.fixture
    def constructor_tool(self, test_config, mock_blockchain_client):
        """Create constructor parameter tool instance."""
        return ConstructorParameter(test_config, mock_blockchain_client)
    
    @pytest.mark.asyncio
    async def test_extract_constructor_params(self, constructor_tool, sample_contract_address):
        """Test extracting constructor parameters."""
        result = await constructor_tool.extract_constructor_params(sample_contract_address, 'ethereum')
        
        assert result['success']
        assert 'parameters' in result
        assert 'creation_transaction' in result
    
    @pytest.mark.asyncio
    async def test_analyze_deployment_context(self, constructor_tool, sample_contract_address):
        """Test analyzing deployment context."""
        context = await constructor_tool.analyze_deployment_context(sample_contract_address, 'ethereum')
        
        assert 'deployer_address' in context
        assert 'block_number' in context
        assert 'timestamp' in context

class TestStateReader:
    """Test cases for StateReader."""
    
    @pytest.fixture
    def state_reader(self, test_config, mock_blockchain_client):
        """Create state reader instance."""
        return StateReader(test_config, mock_blockchain_client)
    
    @pytest.mark.asyncio
    async def test_read_contract_state(self, state_reader, sample_contract_address):
        """Test reading contract state."""
        result = await state_reader.read_contract_state(sample_contract_address, 'ethereum')
        
        assert result['success']
        assert 'state_variables' in result
        assert 'storage_layout' in result
    
    @pytest.mark.asyncio
    async def test_analyze_state_changes(self, state_reader, sample_contract_address):
        """Test analyzing state changes over time."""
        changes = await state_reader.analyze_state_changes(
            sample_contract_address, 
            'ethereum',
            start_block=18000000,
            end_block=18000100
        )
        
        assert 'state_changes' in changes
        assert 'affected_variables' in changes

class TestCodeSanitizer:
    """Test cases for CodeSanitizer."""
    
    @pytest.fixture
    def sanitizer(self, test_config):
        """Create code sanitizer instance."""
        return CodeSanitizer(test_config)
    
    @pytest.mark.asyncio
    async def test_sanitize_exploit_code(self, sanitizer, sample_exploit_code):
        """Test sanitizing exploit code."""
        result = await sanitizer.sanitize_exploit_code(sample_exploit_code)
        
        assert result['success']
        assert 'sanitized_code' in result
        assert 'removed_elements' in result
        assert 'security_score' in result
    
    @pytest.mark.asyncio
    async def test_remove_malicious_patterns(self, sanitizer):
        """Test removing malicious patterns."""
        malicious_code = """
        contract MaliciousContract {
            function destroy() external {
                selfdestruct(payable(msg.sender));
            }
            
            function steal() external {
                // Malicious pattern
                assembly {
                    let ptr := mload(0x40)
                    calldatacopy(ptr, 0, calldatasize())
                    let result := delegatecall(gas(), caller(), ptr, calldatasize(), 0, 0)
                }
            }
        }
        """
        
        result = await sanitizer.sanitize_exploit_code(malicious_code)
        
        assert result['success']
        assert len(result['removed_elements']) > 0
        assert 'selfdestruct' not in result['sanitized_code']

class TestConcreteExecution:
    """Test cases for ConcreteExecution."""
    
    @pytest.fixture
    def executor(self, test_config, mock_blockchain_client):
        """Create concrete execution instance."""
        return ConcreteExecution(test_config, mock_blockchain_client)
    
    @pytest.mark.asyncio
    async def test_execute_exploit_simulation(self, executor, sample_exploit_code, sample_contract_address):
        """Test executing exploit simulation."""
        result = await executor.execute_exploit_simulation(
            exploit_code=sample_exploit_code,
            target_address=sample_contract_address,
            network='ethereum',
            block_number=18000000
        )
        
        assert result['success']
        assert 'execution_result' in result
        assert 'gas_used' in result
        assert 'profit_extracted' in result
    
    @pytest.mark.asyncio
    async def test_validate_execution_safety(self, executor, sample_exploit_code):
        """Test validating execution safety."""
        safety_check = await executor.validate_execution_safety(sample_exploit_code)
        
        assert 'is_safe' in safety_check
        assert 'risk_factors' in safety_check
        assert 'safety_score' in safety_check

class TestRevenueNormalizer:
    """Test cases for RevenueNormalizer."""
    
    @pytest.fixture
    def normalizer(self, test_config, mock_blockchain_client):
        """Create revenue normalizer instance."""
        return RevenueNormalizer(test_config, mock_blockchain_client)
    
    @pytest.mark.asyncio
    async def test_calculate_profit_potential(self, normalizer, sample_contract_address):
        """Test calculating profit potential."""
        result = await normalizer.calculate_profit_potential(
            contract_address=sample_contract_address,
            network='ethereum',
            exploit_type='reentrancy'
        )
        
        assert result['success']
        assert 'profit_potential' in result
        assert 'confidence_score' in result
        assert 'economic_factors' in result
    
    @pytest.mark.asyncio
    async def test_normalize_revenue_metrics(self, normalizer):
        """Test normalizing revenue metrics."""
        raw_metrics = {
            'extracted_eth': 10.5,
            'extracted_tokens': [
                {'symbol': 'USDC', 'amount': 1000, 'decimals': 6},
                {'symbol': 'DAI', 'amount': 500, 'decimals': 18}
            ],
            'gas_costs': 0.05
        }
        
        normalized = await normalizer.normalize_revenue_metrics(raw_metrics, 'ethereum')
        
        assert 'total_usd_value' in normalized
        assert 'net_profit_usd' in normalized
        assert 'roi_percentage' in normalized
    
    @pytest.mark.asyncio
    async def test_economic_validation(self, normalizer, sample_contract_address):
        """Test economic validation of exploit."""
        validation = await normalizer.validate_economic_viability(
            contract_address=sample_contract_address,
            network='ethereum',
            estimated_profit=1000,
            estimated_gas_cost=0.1
        )
        
        assert 'is_viable' in validation
        assert 'profit_margin' in validation
        assert 'risk_assessment' in validation

class TestToolIntegration:
    """Test integration between tools."""
    
    @pytest.fixture
    def all_tools(self, test_config, mock_blockchain_client):
        """Create all tool instances."""
        return {
            'source_fetcher': SourceCodeFetcher(test_config, mock_blockchain_client),
            'constructor': ConstructorParameter(test_config, mock_blockchain_client),
            'state_reader': StateReader(test_config, mock_blockchain_client),
            'sanitizer': CodeSanitizer(test_config),
            'executor': ConcreteExecution(test_config, mock_blockchain_client),
            'normalizer': RevenueNormalizer(test_config, mock_blockchain_client)
        }
    
    @pytest.mark.asyncio
    async def test_tool_workflow_integration(self, all_tools, sample_contract_address):
        """Test complete tool workflow integration."""
        source_result = await all_tools['source_fetcher'].fetch_contract_source(
            sample_contract_address, 'ethereum'
        )
        assert source_result['success']
        
        constructor_result = await all_tools['constructor'].extract_constructor_params(
            sample_contract_address, 'ethereum'
        )
        assert constructor_result['success']
        
        state_result = await all_tools['state_reader'].read_contract_state(
            sample_contract_address, 'ethereum'
        )
        assert state_result['success']
        
        assert source_result['source_code'] is not None
        assert constructor_result['parameters'] is not None
        assert state_result['state_variables'] is not None
    
    def test_tool_performance_tracking(self, all_tools):
        """Test performance tracking across all tools."""
        for tool_name, tool in all_tools.items():
            stats = tool.get_performance_stats()
            
            assert 'total_calls' in stats
            assert 'successful_calls' in stats
            assert 'failed_calls' in stats
            assert 'average_execution_time' in stats
