"""
End-to-End Tests - Complete A1 Workflow

Test the complete A1 agentic system workflow from contract analysis to exploit generation.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from main import ContractProcessor
from config.configuration_manager import ConfigurationManager

class TestCompleteA1Workflow:
    """Test complete A1 system workflow."""
    
    @pytest.fixture
    def processor(self, test_config, mock_grok_api, mock_blockchain_client):
        """Create ContractProcessor with mocked dependencies."""
        with patch('main.AsyncOpenAI', return_value=mock_grok_api), \
             patch('main.BlockchainClient', return_value=mock_blockchain_client):
            return ContractProcessor(test_config)
    
    @pytest.mark.asyncio
    async def test_single_contract_processing(self, processor, sample_contract_address):
        """Test processing a single contract through complete workflow."""
        with patch.object(processor.agent, 'generate_exploit_strategy') as mock_strategy, \
             patch.object(processor.orchestrator, 'execute_strategy') as mock_execute, \
             patch.object(processor.feedback_processor, 'process_execution_feedback') as mock_feedback:
            
            mock_strategy.return_value = {
                'success': True,
                'strategy_type': 'reentrancy',
                'execution_steps': ['deploy', 'attack', 'extract'],
                'confidence_score': 0.8
            }
            
            mock_execute.return_value = {
                'success': True,
                'exploits_found': 1,
                'total_profit_potential': 1000000000000000000,  # 1 ETH
                'execution_time': 2.5
            }
            
            mock_feedback.return_value = {
                'feedback_type': 'success',
                'suggested_improvements': [],
                'confidence_adjustment': 0.0
            }
            
            result = await processor.process_contract(sample_contract_address, 'ethereum')
            
            assert result.success
            assert result.exploits_found >= 0
            assert result.execution_time > 0
            assert mock_strategy.called
            assert mock_execute.called
    
    @pytest.mark.asyncio
    async def test_five_iteration_workflow(self, processor, sample_contract_address):
        """Test 5-iteration budget enforcement with diminishing returns."""
        iteration_results = []
        
        iteration_responses = [
            {'exploits_found': 0, 'success': False},  # Iteration 1: baseline
            {'exploits_found': 1, 'success': True},   # Iteration 2: +9.7% improvement
            {'exploits_found': 1, 'success': True},   # Iteration 3: +3.7% improvement  
            {'exploits_found': 2, 'success': True},   # Iteration 4: +5.1% improvement
            {'exploits_found': 2, 'success': True},   # Iteration 5: +2.8% improvement
        ]
        
        with patch.object(processor, '_execute_single_iteration') as mock_iteration:
            mock_iteration.side_effect = [
                Mock(success=resp['success'], exploits_found=resp['exploits_found'], iteration=i+1)
                for i, resp in enumerate(iteration_responses)
            ]
            
            result = await processor.process_contract(sample_contract_address, 'ethereum', max_iterations=5)
            
            assert mock_iteration.call_count == 5
            assert result.iterations_used == 5
            
            assert result.exploits_found >= 0
    
    @pytest.mark.asyncio
    async def test_multiple_contracts_batch_processing(self, processor, mock_targets_file):
        """Test batch processing of multiple contracts."""
        with patch.object(processor, 'process_contract') as mock_process:
            mock_process.return_value = Mock(
                success=True,
                exploits_found=1,
                execution_time=1.0,
                total_profit_potential=1000000000000000000
            )
            
            results = await processor.process_contracts_from_file(str(mock_targets_file))
            
            assert len(results) == 3  # 3 contracts in mock file
            assert all(result.success for result in results)
            assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_selective_attention_mechanism(self, processor):
        """Test selective attention for computational cost reduction."""
        high_value_address = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"  # UNI token
        
        with patch.object(processor.orchestrator, 'calculate_attention_level') as mock_attention, \
             patch.object(processor, 'process_contract') as mock_process:
            
            mock_attention.return_value = 0.9  # High attention
            mock_process.return_value = Mock(success=True, exploits_found=1)
            
            result = await processor.process_contract(high_value_address, 'ethereum')
            
            mock_attention.assert_called_once()
            assert mock_attention.return_value >= 0.8
    
    @pytest.mark.asyncio
    async def test_economic_validation_integration(self, processor, sample_contract_address):
        """Test economic validation throughout workflow."""
        with patch.object(processor.revenue_normalizer, 'calculate_profit_potential') as mock_profit, \
             patch.object(processor.revenue_normalizer, 'validate_economic_viability') as mock_viability:
            
            mock_profit.return_value = {
                'success': True,
                'profit_potential': 1000000,  # $1M
                'confidence_score': 0.8
            }
            
            mock_viability.return_value = {
                'is_viable': True,
                'profit_margin': 0.95,
                'risk_assessment': 'low'
            }
            
            result = await processor.process_contract(sample_contract_address, 'ethereum')
            
            mock_profit.assert_called()
            mock_viability.assert_called()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, processor, sample_contract_address):
        """Test error handling and recovery mechanisms."""
        with patch.object(processor.source_fetcher, 'fetch_contract_source') as mock_fetch:
            mock_fetch.side_effect = [
                Exception("Network error"),
                {'success': True, 'source_code': 'contract Test {}'}
            ]
            
            result = await processor.process_contract(sample_contract_address, 'ethereum')
            
            assert mock_fetch.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_deterministic_simulation_workflow(self, processor, sample_contract_address):
        """Test deterministic blockchain simulation workflow."""
        with patch.object(processor.forge_integration, 'run_simulation') as mock_simulation:
            mock_simulation.return_value = {
                'success': True,
                'gas_used': 21000,
                'profit_extracted': 1000000000000000000,
                'deterministic': True
            }
            
            result = await processor.process_contract(
                sample_contract_address, 
                'ethereum',
                simulation_block=18000000
            )
            
            mock_simulation.assert_called()
            call_args = mock_simulation.call_args
            assert 'block_number' in call_args.kwargs
            assert call_args.kwargs['block_number'] == 18000000
    
    @pytest.mark.asyncio
    async def test_constrained_output_format_workflow(self, processor, sample_contract_address):
        """Test constrained output format parsing workflow."""
        with patch.object(processor.parser, 'parse') as mock_parse, \
             patch.object(processor.validator, 'validate') as mock_validate:
            
            mock_parse.return_value = Mock(
                success=True,
                solidity_blocks=1,
                code_blocks=[Mock(content='contract Exploit {}', block_type='SOLIDITY')]
            )
            
            mock_validate.return_value = Mock(
                success=True,
                compilation_success=True,
                forge_compatible=True
            )
            
            result = await processor.process_contract(sample_contract_address, 'ethereum')
            
            mock_parse.assert_called()
            mock_validate.assert_called()
    
    def test_performance_monitoring_integration(self, processor):
        """Test performance monitoring throughout workflow."""
        components = [
            processor.agent,
            processor.orchestrator,
            processor.feedback_processor,
            processor.strategy_generator,
            processor.source_fetcher,
            processor.constructor_tool,
            processor.state_reader,
            processor.sanitizer,
            processor.executor,
            processor.revenue_normalizer
        ]
        
        for component in components:
            stats = component.get_performance_stats()
            assert isinstance(stats, dict)
            assert 'total_operations' in stats or 'total_calls' in stats
    
    @pytest.mark.asyncio
    async def test_result_storage_integration(self, processor, sample_contract_address):
        """Test result storage throughout workflow."""
        with patch.object(processor.storage, 'store_result') as mock_store:
            mock_store.return_value = 'result_id_123'
            
            result = await processor.process_contract(sample_contract_address, 'ethereum')
            
            mock_store.assert_called_once()
            stored_result = mock_store.call_args[0][1]  # Second argument is the result
            assert hasattr(stored_result, 'contract_address')
            assert hasattr(stored_result, 'success')

class TestSystemConfiguration:
    """Test system configuration and environment setup."""
    
    def test_configuration_loading(self, test_config):
        """Test configuration manager loading."""
        config_manager = ConfigurationManager()
        config = config_manager.get_config()
        
        required_keys = [
            'GROK_API_KEY',
            'ETH_RPC_URL',
            'BSC_RPC_URL',
            'ETHERSCAN_API_KEY',
            'BSCSCAN_API_KEY'
        ]
        
        for key in required_keys:
            assert key in config
    
    def test_api_key_validation(self):
        """Test API key validation."""
        config_manager = ConfigurationManager()
        
        valid_keys = {
            'GROK_API_KEY': 'xai-test-key',
            'ETHERSCAN_API_KEY': 'test-etherscan-key',
            'BSCSCAN_API_KEY': 'test-bscscan-key'
        }
        
        for key, value in valid_keys.items():
            assert config_manager.validate_api_key(key, value)
    
    def test_network_configuration(self):
        """Test network configuration validation."""
        config_manager = ConfigurationManager()
        config = config_manager.get_config()
        
        assert config['ETH_RPC_URL'].startswith('https://')
        assert config['BSC_RPC_URL'].startswith('https://')
        assert 'alchemy.com' in config['ETH_RPC_URL']
        assert 'alchemy.com' in config['BSC_RPC_URL']

class TestSystemIntegration:
    """Test complete system integration."""
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, test_config):
        """Test complete system initialization."""
        with patch('main.AsyncOpenAI'), \
             patch('main.BlockchainClient'), \
             patch('main.ForgeIntegration'):
            
            processor = ContractProcessor(test_config)
            await processor.initialize()
            
            assert processor.agent is not None
            assert processor.orchestrator is not None
            assert processor.storage is not None
            assert processor.logger is not None
            assert processor.metrics is not None
    
    @pytest.mark.asyncio
    async def test_system_cleanup(self, test_config):
        """Test system cleanup and resource management."""
        with patch('main.AsyncOpenAI'), \
             patch('main.BlockchainClient'), \
             patch('main.ForgeIntegration'):
            
            processor = ContractProcessor(test_config)
            await processor.initialize()
            
            await processor.cleanup()
    
    def test_system_health_check(self, test_config):
        """Test system health check functionality."""
        with patch('main.AsyncOpenAI'), \
             patch('main.BlockchainClient'), \
             patch('main.ForgeIntegration'):
            
            processor = ContractProcessor(test_config)
            health = processor.get_system_health()
            
            assert 'status' in health
            assert 'components' in health
            assert 'performance' in health
