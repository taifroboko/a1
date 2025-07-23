"""
Unit Tests - Core Components

Test the core agentic system components.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from core.agent import A1Agent
from core.orchestrator import ToolOrchestrator
from core.feedback import FeedbackProcessor
from core.strategy import StrategyGenerator

class TestA1Agent:
    """Test cases for A1Agent."""
    
    @pytest.fixture
    def agent(self, test_config, mock_grok_api):
        """Create A1Agent instance."""
        with patch('core.agent.AsyncOpenAI', return_value=mock_grok_api):
            return A1Agent(test_config)
    
    @pytest.mark.asyncio
    async def test_generate_exploit_strategy(self, agent, sample_contract_address):
        """Test exploit strategy generation."""
        context = {
            'contract_address': sample_contract_address,
            'source_code': 'contract Test {}',
            'network': 'ethereum'
        }
        
        strategy = await agent.generate_exploit_strategy(context)
        
        assert strategy['success']
        assert 'strategy_type' in strategy
        assert 'execution_steps' in strategy
        assert 'confidence_score' in strategy
    
    @pytest.mark.asyncio
    async def test_iterative_refinement(self, agent, sample_contract_address):
        """Test iterative strategy refinement."""
        initial_context = {
            'contract_address': sample_contract_address,
            'source_code': 'contract Test {}',
            'network': 'ethereum'
        }
        
        feedback = {
            'previous_attempts': 2,
            'failed_strategies': ['reentrancy', 'overflow'],
            'execution_errors': ['insufficient_gas', 'revert']
        }
        
        refined_strategy = await agent.refine_strategy(initial_context, feedback)
        
        assert refined_strategy['success']
        assert refined_strategy['iteration'] > 1
        assert 'improvements' in refined_strategy
    
    @pytest.mark.asyncio
    async def test_five_iteration_budget(self, agent, sample_contract_address):
        """Test 5-iteration budget enforcement."""
        context = {
            'contract_address': sample_contract_address,
            'source_code': 'contract Test {}',
            'network': 'ethereum'
        }
        
        for iteration in range(1, 6):
            strategy = await agent.generate_exploit_strategy(context, iteration=iteration)
            assert strategy['iteration'] == iteration
            assert strategy['iteration'] <= 5
        
        strategy = await agent.generate_exploit_strategy(context, iteration=6)
        assert not strategy['success'] or strategy['iteration'] <= 5

class TestToolOrchestrator:
    """Test cases for ToolOrchestrator."""
    
    @pytest.fixture
    def orchestrator(self, test_config, mock_blockchain_client):
        """Create ToolOrchestrator instance."""
        return ToolOrchestrator(test_config, mock_blockchain_client)
    
    @pytest.mark.asyncio
    async def test_orchestrate_tool_execution(self, orchestrator, sample_contract_address):
        """Test orchestrating tool execution."""
        strategy = {
            'tools_required': ['source_fetcher', 'state_reader', 'executor'],
            'execution_order': ['source_fetcher', 'state_reader', 'executor'],
            'parameters': {
                'contract_address': sample_contract_address,
                'network': 'ethereum'
            }
        }
        
        result = await orchestrator.execute_strategy(strategy)
        
        assert result['success']
        assert 'tool_results' in result
        assert len(result['tool_results']) == 3
    
    @pytest.mark.asyncio
    async def test_selective_attention_mechanism(self, orchestrator, sample_contract_address):
        """Test selective attention for computational cost reduction."""
        high_value_context = {
            'contract_address': sample_contract_address,
            'estimated_value': 1000000,  # $1M
            'complexity_score': 0.8
        }
        
        attention_level = await orchestrator.calculate_attention_level(high_value_context)
        assert attention_level >= 0.8
        
        low_value_context = {
            'contract_address': sample_contract_address,
            'estimated_value': 100,  # $100
            'complexity_score': 0.2
        }
        
        attention_level = await orchestrator.calculate_attention_level(low_value_context)
        assert attention_level <= 0.5
    
    @pytest.mark.asyncio
    async def test_tool_failure_handling(self, orchestrator, sample_contract_address):
        """Test handling tool execution failures."""
        strategy = {
            'tools_required': ['source_fetcher', 'invalid_tool', 'state_reader'],
            'execution_order': ['source_fetcher', 'invalid_tool', 'state_reader'],
            'parameters': {
                'contract_address': sample_contract_address,
                'network': 'ethereum'
            }
        }
        
        result = await orchestrator.execute_strategy(strategy)
        
        assert 'tool_results' in result
        assert 'failed_tools' in result
        assert 'invalid_tool' in result['failed_tools']

class TestFeedbackProcessor:
    """Test cases for FeedbackProcessor."""
    
    @pytest.fixture
    def feedback_processor(self, test_config):
        """Create FeedbackProcessor instance."""
        return FeedbackProcessor(test_config)
    
    @pytest.mark.asyncio
    async def test_process_execution_feedback(self, feedback_processor):
        """Test processing execution feedback."""
        execution_result = {
            'success': False,
            'error_type': 'revert',
            'error_message': 'insufficient balance',
            'gas_used': 21000,
            'execution_time': 0.5
        }
        
        feedback = await feedback_processor.process_execution_feedback(execution_result)
        
        assert 'feedback_type' in feedback
        assert 'suggested_improvements' in feedback
        assert 'confidence_adjustment' in feedback
    
    @pytest.mark.asyncio
    async def test_analyze_diminishing_returns(self, feedback_processor):
        """Test analyzing diminishing returns pattern."""
        iteration_results = [
            {'iteration': 1, 'exploits_found': 0, 'success': False},
            {'iteration': 2, 'exploits_found': 1, 'success': True},  # +9.7% improvement
            {'iteration': 3, 'exploits_found': 1, 'success': True},  # +3.7% improvement
            {'iteration': 4, 'exploits_found': 2, 'success': True},  # +5.1% improvement
            {'iteration': 5, 'exploits_found': 2, 'success': True},  # +2.8% improvement
        ]
        
        analysis = await feedback_processor.analyze_diminishing_returns(iteration_results)
        
        assert 'improvement_rates' in analysis
        assert 'diminishing_pattern' in analysis
        assert 'stop_recommendation' in analysis
    
    @pytest.mark.asyncio
    async def test_feedback_learning(self, feedback_processor):
        """Test feedback learning and adaptation."""
        historical_feedback = [
            {'strategy': 'reentrancy', 'success': True, 'profit': 1000},
            {'strategy': 'reentrancy', 'success': False, 'error': 'revert'},
            {'strategy': 'overflow', 'success': True, 'profit': 500},
        ]
        
        learned_patterns = await feedback_processor.learn_from_feedback(historical_feedback)
        
        assert 'strategy_success_rates' in learned_patterns
        assert 'common_failure_patterns' in learned_patterns
        assert 'recommended_strategies' in learned_patterns

class TestStrategyGenerator:
    """Test cases for StrategyGenerator."""
    
    @pytest.fixture
    def strategy_generator(self, test_config, mock_grok_api):
        """Create StrategyGenerator instance."""
        with patch('core.strategy.AsyncOpenAI', return_value=mock_grok_api):
            return StrategyGenerator(test_config)
    
    @pytest.mark.asyncio
    async def test_generate_initial_strategy(self, strategy_generator, sample_contract_address):
        """Test generating initial exploit strategy."""
        context = {
            'contract_address': sample_contract_address,
            'source_code': 'contract Test {}',
            'vulnerability_hints': ['reentrancy', 'overflow'],
            'network': 'ethereum'
        }
        
        strategy = await strategy_generator.generate_strategy(context)
        
        assert strategy['success']
        assert 'strategy_type' in strategy
        assert 'execution_plan' in strategy
        assert 'expected_profit' in strategy
    
    @pytest.mark.asyncio
    async def test_strategy_adaptation(self, strategy_generator, sample_contract_address):
        """Test strategy adaptation based on feedback."""
        initial_context = {
            'contract_address': sample_contract_address,
            'source_code': 'contract Test {}',
            'network': 'ethereum'
        }
        
        feedback = {
            'failed_attempts': ['reentrancy', 'overflow'],
            'execution_errors': ['insufficient_gas'],
            'suggested_improvements': ['increase_gas_limit', 'try_flashloan']
        }
        
        adapted_strategy = await strategy_generator.adapt_strategy(initial_context, feedback)
        
        assert adapted_strategy['success']
        assert adapted_strategy['strategy_type'] not in feedback['failed_attempts']
        assert 'adaptations' in adapted_strategy
    
    @pytest.mark.asyncio
    async def test_economic_validation_integration(self, strategy_generator, sample_contract_address):
        """Test integration with economic validation."""
        context = {
            'contract_address': sample_contract_address,
            'source_code': 'contract Test {}',
            'network': 'ethereum',
            'estimated_balance': 1000000  # $1M
        }
        
        strategy = await strategy_generator.generate_strategy(context, validate_economics=True)
        
        assert strategy['success']
        assert 'economic_validation' in strategy
        assert 'profit_potential' in strategy
        assert 'cost_benefit_ratio' in strategy

class TestCoreIntegration:
    """Test integration between core components."""
    
    @pytest.fixture
    def core_system(self, test_config, mock_grok_api, mock_blockchain_client):
        """Create integrated core system."""
        with patch('core.agent.AsyncOpenAI', return_value=mock_grok_api), \
             patch('core.strategy.AsyncOpenAI', return_value=mock_grok_api):
            
            return {
                'agent': A1Agent(test_config),
                'orchestrator': ToolOrchestrator(test_config, mock_blockchain_client),
                'feedback': FeedbackProcessor(test_config),
                'strategy': StrategyGenerator(test_config)
            }
    
    @pytest.mark.asyncio
    async def test_complete_agent_workflow(self, core_system, sample_contract_address):
        """Test complete agent workflow integration."""
        context = {
            'contract_address': sample_contract_address,
            'source_code': 'contract Test {}',
            'network': 'ethereum'
        }
        
        strategy = await core_system['strategy'].generate_strategy(context)
        assert strategy['success']
        
        execution_result = await core_system['orchestrator'].execute_strategy(strategy)
        
        feedback = await core_system['feedback'].process_execution_feedback(execution_result)
        
        refined_strategy = await core_system['agent'].refine_strategy(context, feedback)
        
        assert refined_strategy['success']
        assert refined_strategy['iteration'] > 1
    
    def test_performance_monitoring(self, core_system):
        """Test performance monitoring across core components."""
        for component_name, component in core_system.items():
            stats = component.get_performance_stats()
            
            assert 'total_operations' in stats
            assert 'successful_operations' in stats
            assert 'average_execution_time' in stats
