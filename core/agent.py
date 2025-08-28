"""
Agent Controller - A1 Agentic System

Main agent controller with Grok-4-0709 integration and 5-iteration budget management.
Implements the core autonomous agent that orchestrates exploit generation through
iterative refinement with diminishing returns tracking.

Based on the A1 research paper specifications.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import openai
from openai import AsyncOpenAI

from tools.source_code_fetcher import SourceCodeFetcher
from tools.constructor_parameter import ConstructorParameterTool
from tools.state_reader import BlockchainStateReader
from tools.code_sanitizer import CodeSanitizer
from tools.concrete_execution import ConcreteExecutionTool
from tools.revenue_normalizer import RevenueNormalizer

logger = logging.getLogger(__name__)

class IterationPhase(Enum):
    """Phases of the 5-iteration exploit generation process"""
    RECONNAISSANCE = "reconnaissance"
    ANALYSIS = "analysis"
    STRATEGY_GENERATION = "strategy_generation"
    EXECUTION_PLANNING = "execution_planning"
    VALIDATION = "validation"

@dataclass
class IterationResult:
    """Container for iteration execution results"""
    iteration_number: int
    phase: IterationPhase
    success: bool
    findings: Dict[str, Any]
    strategy_updates: List[Dict[str, Any]]
    confidence_score: float
    execution_time: float
    token_usage: Dict[str, int]
    error_message: Optional[str] = None

@dataclass
class ExploitStrategy:
    """Container for exploit strategy information"""
    strategy_id: str
    target_contract: str
    vulnerability_type: str
    attack_vector: str
    preconditions: List[Dict[str, Any]]
    execution_steps: List[Dict[str, Any]]
    expected_profit_usd: float
    confidence_score: float
    risk_assessment: Dict[str, Any]
    validation_status: str
    created_at: int
    updated_at: int

@dataclass
class AgentState:
    """Container for agent state tracking"""
    current_iteration: int
    current_phase: IterationPhase
    target_contract: str
    total_budget_used: int
    iteration_budgets: List[int]
    strategies_generated: List[ExploitStrategy]
    findings_history: List[Dict[str, Any]]
    confidence_progression: List[float]
    diminishing_returns_factor: float
    session_start_time: int

class A1Agent:
    """
    Main A1 Agent Controller with Grok-4-0709 integration.

    Implements the autonomous agent that orchestrates exploit generation
    through iterative refinement with 5-iteration budget management.
    """

    def __init__(self, config: Dict[str, Any], result_storage=None):
        """
        Initialize the A1 Agent.

        Args:
            config: Configuration dictionary with API keys and settings
            result_storage: ResultStorage instance for caching
        """
        self.config = config
        self.result_storage = result_storage
        
        self.grok_client = AsyncOpenAI(
            api_key=config.get('GROK_API_KEY'),
            base_url=config.get('GROK_BASE_URL', 'https://api.x.ai/v1')
        )
        
        self.tools = self._initialize_tools()
        
        self.max_iterations = config.get('MAX_ITERATIONS', 5)
        self.base_budget_per_iteration = config.get('BASE_BUDGET_PER_ITERATION', 1000)
        self.diminishing_factor = config.get('DIMINISHING_FACTOR', 0.8)
        self.confidence_threshold = config.get('CONFIDENCE_THRESHOLD', 0.7)
        
        self.state: Optional[AgentState] = None
        
        self.phase_prompts = self._initialize_phase_prompts()
        
        self.attention_weights = {
            'source_code': 1.0,
            'constructor_params': 0.8,
            'state_analysis': 0.9,
            'code_sanitization': 0.6,
            'execution_simulation': 1.0,
            'revenue_analysis': 0.9
        }
    
    def _initialize_tools(self) -> Dict[str, Any]:
        """Initialize all domain-specific tools."""
        from web3 import Web3
        
        ethereum_client = Web3(Web3.HTTPProvider(self.config['ETHEREUM_RPC_URL']))
        bsc_client = Web3(Web3.HTTPProvider(self.config['BSC_RPC_URL']))
        
        web3_clients = {
            'ethereum': ethereum_client,
            'bsc': bsc_client
        }
        
        return {
            'source_code_fetcher': SourceCodeFetcher(
                web3_client=ethereum_client,
                etherscan_api_key=self.config['ETHERSCAN_API_KEY'],
                bscscan_api_key=self.config['BSCSCAN_API_KEY']
            ),
            'constructor_parameter': ConstructorParameterTool(
                web3_client=ethereum_client,
                etherscan_api_key=self.config['ETHERSCAN_API_KEY'],
                bscscan_api_key=self.config['BSCSCAN_API_KEY']
            ),
            'state_reader': BlockchainStateReader(ethereum_client),
            'code_sanitizer': CodeSanitizer(),
            'concrete_execution': ConcreteExecutionTool(
                ethereum_rpc_url=self.config['ETHEREUM_RPC_URL'],
                bsc_rpc_url=self.config['BSC_RPC_URL']
            ),
            'revenue_normalizer': RevenueNormalizer(web3_clients)
        }
    
    def _initialize_phase_prompts(self) -> Dict[IterationPhase, str]:
        """Initialize prompts for each iteration phase."""
        return {
            IterationPhase.RECONNAISSANCE: """
You are an expert smart contract security researcher analyzing a target contract for potential vulnerabilities.

TASK: Perform comprehensive reconnaissance on the target contract to identify attack surfaces and potential vulnerabilities.

FOCUS AREAS:
1. Contract architecture and inheritance patterns
2. External dependencies and library usage
3. Access control mechanisms and privilege escalation vectors
4. Token economics and balance manipulation opportunities
5. Reentrancy and state manipulation vulnerabilities
6. Oracle dependencies and price manipulation vectors

ANALYSIS APPROACH:
- Examine source code for common vulnerability patterns
- Analyze constructor parameters for configuration weaknesses
- Review state variables for manipulation opportunities
- Identify external calls and trust boundaries
- Map token flow and balance tracking mechanisms

Provide a structured analysis with specific findings, potential attack vectors, and confidence assessments.
""",
            
            IterationPhase.ANALYSIS: """
You are an expert smart contract security researcher performing deep vulnerability analysis.

TASK: Conduct detailed analysis of identified attack surfaces to determine exploitability and impact.

ANALYSIS DEPTH:
1. Vulnerability classification and severity assessment
2. Exploit feasibility analysis with technical constraints
3. Economic impact estimation and profit potential
4. Attack complexity and resource requirements
5. Detection probability and mitigation difficulty

TECHNICAL FOCUS:
- State manipulation attack vectors
- Reentrancy exploitation opportunities
- Access control bypass techniques
- Economic arbitrage and MEV opportunities
- Flash loan attack possibilities
- Cross-function interaction vulnerabilities

Provide detailed technical analysis with exploit scenarios, economic assessments, and risk evaluations.
""",
            
            IterationPhase.STRATEGY_GENERATION: """
You are an expert smart contract exploit developer creating actionable attack strategies.

TASK: Generate concrete exploit strategies based on vulnerability analysis with step-by-step execution plans.

STRATEGY COMPONENTS:
1. Exploit vector selection and optimization
2. Transaction sequence planning and ordering
3. Resource requirement estimation (gas, capital, timing)
4. Profit maximization techniques
5. Risk mitigation and stealth considerations
6. Fallback strategies and contingency planning

EXECUTION PLANNING:
- Detailed transaction sequences with parameters
- Gas optimization and MEV protection strategies
- Timing constraints and block dependency analysis
- Capital requirements and funding strategies
- Profit extraction and laundering mechanisms

Generate multiple strategy variants with profitability rankings and execution complexity assessments.
""",
            
            IterationPhase.EXECUTION_PLANNING: """
You are an expert smart contract exploit engineer finalizing execution plans for maximum success probability.

TASK: Create detailed execution plans with precise transaction parameters and timing requirements.

EXECUTION DETAILS:
1. Transaction construction with exact parameters
2. Gas estimation and optimization strategies
3. Timing coordination and block targeting
4. MEV protection and front-running mitigation
5. Error handling and recovery mechanisms
6. Profit extraction optimization

TECHNICAL SPECIFICATIONS:
- Solidity contract code for exploit execution
- Transaction calldata construction
- State dependency management
- Slippage protection and price impact analysis
- Monitoring and alerting mechanisms

Provide production-ready execution plans with comprehensive risk management and profit optimization.
""",
            
            IterationPhase.VALIDATION: """
You are an expert smart contract security validator ensuring exploit strategy viability and profitability.

TASK: Validate exploit strategies through comprehensive testing and economic analysis.

VALIDATION CRITERIA:
1. Technical feasibility verification
2. Economic profitability confirmation
3. Risk assessment and mitigation validation
4. Execution complexity evaluation
5. Detection probability analysis
6. Legal and ethical considerations

TESTING APPROACH:
- Forge-based simulation testing
- Historical data backtesting
- Economic model validation
- Gas cost optimization verification
- Slippage and MEV impact analysis

Provide final recommendations with confidence scores, profit projections, and risk assessments.
"""
        }
    
    async def initialize_session(self, target_contract: str, chain: str = 'ethereum') -> str:
        """
        Initialize a new exploit generation session.
        
        Args:
            target_contract: Target contract address
            chain: Blockchain network ('ethereum' or 'bsc')
            
        Returns:
            Session ID for tracking
        """
        session_id = f"a1_{int(time.time())}_{target_contract[:8]}"
        
        self.state = AgentState(
            current_iteration=0,
            current_phase=IterationPhase.RECONNAISSANCE,
            target_contract=target_contract,
            total_budget_used=0,
            iteration_budgets=[],
            strategies_generated=[],
            findings_history=[],
            confidence_progression=[],
            diminishing_returns_factor=1.0,
            session_start_time=int(time.time())
        )
        
        logger.info(f"Initialized A1 session {session_id} for contract {target_contract}")
        return session_id
    
    async def execute_full_analysis(self, target_contract: str, chain: str = 'ethereum', force: bool = False, reuse: bool = False) -> Dict[str, Any]:
        """Execute the complete analysis process with optional caching."""
        session_id = await self.initialize_session(target_contract, chain)

        source_info = await self._fetch_source_code()
        contract_info = None
        if 'source_code' in source_info and 'abi' in source_info:
            class ContractInfo:
                def __init__(self, abi, source_code, contract_name):
                    self.abi = abi
                    self.source_code = source_code
                    self.contract_name = contract_name

            contract_info = ContractInfo(
                abi=source_info.get('abi', []),
                source_code=source_info.get('source_code', ''),
                contract_name=source_info.get('contract_name', 'Unknown')
            )

        state_snapshot = await self._capture_state_snapshot(contract_info) if contract_info else {}
        source_hash = hashlib.sha256(source_info.get('source_code', '').encode()).hexdigest()
        state_hash = hashlib.sha256(json.dumps(state_snapshot.get('state_data', {}), sort_keys=True).encode()).hexdigest()

        if self.result_storage:
            cached_id = await self.result_storage.get_cached_result_id(target_contract, chain, source_hash, state_hash)
            if cached_id and not force:
                logger.info(f"Cache hit for {target_contract} on {chain}")
                if reuse:
                    cached_result = await self.result_storage.load_result(cached_id)
                    if cached_result:
                        cached_result['cached'] = True
                        cached_result['source_hash'] = source_hash
                        cached_result['state_hash'] = state_hash
                        return cached_result
                return {
                    'cached': True,
                    'source_hash': source_hash,
                    'state_hash': state_hash,
                    'success': True,
                    'strategies': [],
                    'exploits': [],
                    'total_profit_potential': 0.0,
                    'confidence_score': 1.0,
                    'iterations_used': 0,
                    'detailed_results': {}
                }

        logger.info(f"Starting full A1 analysis for {target_contract}")

        iteration_results = []

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Executing iteration {iteration}/{self.max_iterations}")

            iteration_budget = int(
                self.base_budget_per_iteration *
                (self.diminishing_factor ** (iteration - 1))
            )

            self.state.current_iteration = iteration
            self.state.iteration_budgets.append(iteration_budget)

            result = await self._execute_iteration(iteration, iteration_budget)
            iteration_results.append(result)

            self.state.total_budget_used += result.token_usage.get('total_tokens', 0)
            self.state.confidence_progression.append(result.confidence_score)
            self.state.findings_history.append(result.findings)

            if self._should_terminate_early(iteration_results):
                logger.info(f"Early termination at iteration {iteration}")
                break

            await asyncio.sleep(1)

        final_analysis = await self._generate_final_analysis(iteration_results)

        logger.info(f"Completed A1 analysis for {target_contract}")
        return {
            'success': True,
            'strategies': [asdict(s) for s in self.state.strategies_generated],
            'exploits': [],
            'total_profit_potential': sum(s.expected_profit_usd for s in self.state.strategies_generated),
            'confidence_score': final_analysis.get('session_summary', {}).get('final_confidence', 0.0),
            'iterations_used': len(iteration_results),
            'detailed_results': final_analysis,
            'source_hash': source_hash,
            'state_hash': state_hash
        }
    
    async def _execute_iteration(self, iteration_number: int, budget: int) -> IterationResult:
        """
        Execute a single iteration of the exploit generation process.
        
        Args:
            iteration_number: Current iteration number (1-5)
            budget: Token budget for this iteration
            
        Returns:
            IterationResult with findings and updates
        """
        start_time = time.time()
        
        phase = self._get_iteration_phase(iteration_number)
        self.state.current_phase = phase
        
        logger.info(f"Executing iteration {iteration_number} - Phase: {phase.value}")
        
        try:
            context = await self._gather_iteration_context(phase)
            
            prompt = await self._generate_iteration_prompt(phase, context, iteration_number)
            
            grok_response = await self._execute_grok_analysis(prompt, budget)
            
            findings = await self._process_grok_response(grok_response, phase)
            
            strategy_updates = await self._update_strategies(findings, phase)
            
            confidence_score = self._calculate_confidence_score(findings, iteration_number)
            
            execution_time = time.time() - start_time
            
            return IterationResult(
                iteration_number=iteration_number,
                phase=phase,
                success=True,
                findings=findings,
                strategy_updates=strategy_updates,
                confidence_score=confidence_score,
                execution_time=execution_time,
                token_usage=grok_response.get('usage', {})
            )
            
        except Exception as e:
            logger.error(f"Iteration {iteration_number} failed: {e}")
            
            return IterationResult(
                iteration_number=iteration_number,
                phase=phase,
                success=False,
                findings={},
                strategy_updates=[],
                confidence_score=0.0,
                execution_time=time.time() - start_time,
                token_usage={},
                error_message=str(e)
            )
    
    def _get_iteration_phase(self, iteration_number: int) -> IterationPhase:
        """Determine the phase for a given iteration number."""
        phase_mapping = {
            1: IterationPhase.RECONNAISSANCE,
            2: IterationPhase.ANALYSIS,
            3: IterationPhase.STRATEGY_GENERATION,
            4: IterationPhase.EXECUTION_PLANNING,
            5: IterationPhase.VALIDATION
        }
        return phase_mapping.get(iteration_number, IterationPhase.VALIDATION)
    
    async def _gather_iteration_context(self, phase: IterationPhase) -> Dict[str, Any]:
        """
        Gather relevant context from tools based on iteration phase.
        
        Args:
            phase: Current iteration phase
            
        Returns:
            Context dictionary with tool outputs
        """
        context = {
            'target_contract': self.state.target_contract,
            'previous_findings': self.state.findings_history,
            'current_strategies': self.state.strategies_generated
        }
        
        if phase == IterationPhase.RECONNAISSANCE:
            if self.attention_weights['source_code'] > 0.5:
                context['source_code'] = await self._fetch_source_code()
            
            if self.attention_weights['constructor_params'] > 0.5:
                context['constructor_params'] = await self._analyze_constructor_params()
        
        elif phase == IterationPhase.ANALYSIS:
            if self.attention_weights['state_analysis'] > 0.5:
                context['state_snapshot'] = await self._capture_state_snapshot()
            
            if self.attention_weights['code_sanitization'] > 0.5:
                context['sanitized_code'] = await self._sanitize_code()
        
        elif phase == IterationPhase.STRATEGY_GENERATION:
            context['comprehensive_analysis'] = await self._gather_comprehensive_context()
        
        elif phase == IterationPhase.EXECUTION_PLANNING:
            if self.attention_weights['execution_simulation'] > 0.8:
                context['simulation_results'] = await self._simulate_execution()
        
        elif phase == IterationPhase.VALIDATION:
            if self.attention_weights['revenue_analysis'] > 0.5:
                context['revenue_analysis'] = await self._analyze_revenue_potential()
        
        return context
    
    async def _fetch_source_code(self) -> Dict[str, Any]:
        """Fetch and analyze source code using the Source Code Fetcher tool."""
        try:
            fetcher = self.tools['source_code_fetcher']
            
            chain = 'ethereum'  # Default, could be enhanced with chain detection
            
            contract_info = await fetcher.fetch_contract_source(
                self.state.target_contract, 
                chain
            )
            
            return {
                'source_code': contract_info.source_code,
                'contract_name': getattr(contract_info, 'contract_name', 'Unknown'),
                'compiler_version': contract_info.compiler_version,
                'is_proxy': getattr(contract_info, 'proxy_type', None) is not None,
                'implementation_address': contract_info.implementation_address,
                'proxy_type': contract_info.proxy_type,
                'abi': contract_info.abi
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch source code: {e}")
            return {'error': str(e)}
    
    async def _analyze_constructor_params(self, contract_info=None) -> Dict[str, Any]:
        """Analyze constructor parameters using the Constructor Parameter tool."""
        try:
            constructor_tool = self.tools['constructor_parameter']
            
            if contract_info and hasattr(contract_info, 'abi') and contract_info.abi:
                constructor_info = await constructor_tool.analyze_constructor_parameters(
                    self.state.target_contract, contract_info.abi
                )
            else:
                logger.warning("No contract ABI available for constructor analysis")
                return {'error': 'No ABI available'}
            
            return {
                'deployment_tx': constructor_info.deployment_tx_hash,
                'parameters': constructor_info.parameters,
                'decoded_params': constructor_info.decoded_parameters,
                'analysis': constructor_info.analysis_summary
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze constructor parameters: {e}")
            return {'error': str(e)}
    
    async def _capture_state_snapshot(self, contract_info=None) -> Dict[str, Any]:
        """Capture state snapshot using the State Reader tool."""
        try:
            state_reader = self.tools['state_reader']
            
            if contract_info and hasattr(contract_info, 'abi') and contract_info.abi:
                snapshot = await state_reader.capture_state_snapshot(
                    self.state.target_contract,
                    contract_info.abi
                )
            else:
                logger.warning("No contract ABI available for state snapshot")
                return {'error': 'No ABI available'}
            
            return {
                'block_number': snapshot.block_number,
                'timestamp': snapshot.timestamp,
                'state_data': snapshot.state_data,
                'view_functions': snapshot.view_functions,
                'balance': snapshot.balance
            }
            
        except Exception as e:
            logger.error(f"Failed to capture state snapshot: {e}")
            return {'error': str(e)}
    
    async def _sanitize_code(self) -> Dict[str, Any]:
        """Sanitize code using the Code Sanitizer tool."""
        try:
            sanitizer = self.tools['code_sanitizer']
            
            source_code = ""  # Would be retrieved from context
            
            sanitized = sanitizer.sanitize_contract_code(source_code)
            
            return {
                'sanitized_code': sanitized.sanitized_code,
                'removed_comments': len(sanitized.removed_comments),
                'removed_imports': len(sanitized.removed_imports),
                'optimization_summary': sanitized.optimization_summary
            }
            
        except Exception as e:
            logger.error(f"Failed to sanitize code: {e}")
            return {'error': str(e)}
    
    async def _gather_comprehensive_context(self) -> Dict[str, Any]:
        """Gather comprehensive context for strategy generation."""
        context = {}
        
        source_result = await self._fetch_source_code()
        context['source_analysis'] = source_result if not isinstance(source_result, Exception) else {}
        
        contract_info = None
        if 'source_code' in source_result and 'abi' in source_result:
            class ContractInfo:
                def __init__(self, abi, source_code, contract_name):
                    self.abi = abi
                    self.source_code = source_code
                    self.contract_name = contract_name
            
            contract_info = ContractInfo(
                abi=source_result.get('abi', []),
                source_code=source_result.get('source_code', ''),
                contract_name=source_result.get('contract_name', 'Unknown')
            )
        
        tasks = [
            self._analyze_constructor_params(contract_info),
            self._capture_state_snapshot(contract_info),
            self._sanitize_code()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        context['constructor_analysis'] = results[0] if not isinstance(results[0], Exception) else {}
        context['state_analysis'] = results[1] if not isinstance(results[1], Exception) else {}
        context['code_analysis'] = results[2] if not isinstance(results[2], Exception) else {}
        
        return context
    
    async def _simulate_execution(self) -> Dict[str, Any]:
        """Simulate execution using the Concrete Execution tool."""
        try:
            execution_tool = self.tools['concrete_execution']
            
            fork_id = await execution_tool.create_blockchain_fork('ethereum')
            
            project_path = await execution_tool.setup_forge_project(
                f"test_{self.state.target_contract[:8]}", 
                fork_id
            )
            
            return {
                'fork_id': fork_id,
                'project_path': project_path,
                'simulation_ready': True
            }
            
        except Exception as e:
            logger.error(f"Failed to simulate execution: {e}")
            return {'error': str(e)}
    
    async def _analyze_revenue_potential(self) -> Dict[str, Any]:
        """Analyze revenue potential using the Revenue Normalizer tool."""
        try:
            revenue_tool = self.tools['revenue_normalizer']
            
            snapshots = await revenue_tool.capture_balance_snapshot(
                self.state.target_contract,
                [],  # Token addresses would be determined from analysis
                1    # Ethereum chain ID
            )
            
            return {
                'balance_snapshots': len(snapshots),
                'total_value_locked': sum(s.balance_usd or 0 for s in snapshots),
                'revenue_potential': 'high' if sum(s.balance_usd or 0 for s in snapshots) > 100000 else 'medium'
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze revenue potential: {e}")
            return {'error': str(e)}
    
    async def _generate_iteration_prompt(self, phase: IterationPhase, context: Dict[str, Any], iteration: int) -> str:
        """
        Generate the prompt for Grok-4-0709 based on phase and context.
        
        Args:
            phase: Current iteration phase
            context: Gathered context from tools
            iteration: Current iteration number
            
        Returns:
            Formatted prompt string
        """
        base_prompt = self.phase_prompts[phase]
        
        context_section = "\n\nCONTEXT INFORMATION:\n"
        context_section += f"Target Contract: {self.state.target_contract}\n"
        context_section += f"Iteration: {iteration}/{self.max_iterations}\n"
        
        if 'source_code' in context:
            context_section += f"\nSource Code Analysis:\n{json.dumps(context['source_code'], indent=2)}\n"
        
        if 'constructor_params' in context:
            context_section += f"\nConstructor Analysis:\n{json.dumps(context['constructor_params'], indent=2)}\n"
        
        if 'state_snapshot' in context:
            context_section += f"\nState Analysis:\n{json.dumps(context['state_snapshot'], indent=2)}\n"
        
        if self.state.findings_history:
            context_section += f"\nPrevious Findings:\n{json.dumps(self.state.findings_history[-2:], indent=2)}\n"
        
        if self.state.strategies_generated:
            strategies_summary = [
                {
                    'id': s.strategy_id,
                    'type': s.vulnerability_type,
                    'confidence': s.confidence_score
                }
                for s in self.state.strategies_generated[-3:]  # Last 3 strategies
            ]
            context_section += f"\nCurrent Strategies:\n{json.dumps(strategies_summary, indent=2)}\n"
        
        output_format = """
\nOUTPUT FORMAT:
Provide your analysis in the following JSON structure:
{
    "phase": "current_phase",
    "findings": {
        "vulnerabilities": [...],
        "attack_vectors": [...],
        "economic_opportunities": [...],
        "technical_constraints": [...]
    },
    "strategies": [
        {
            "strategy_id": "unique_id",
            "vulnerability_type": "type",
            "attack_vector": "vector",
            "confidence_score": 0.0-1.0,
            "expected_profit_usd": 0,
            "execution_steps": [...],
            "preconditions": [...],
            "risk_assessment": {...}
        }
    ],
    "recommendations": [...],
    "confidence_score": 0.0-1.0
}
"""
        
        return base_prompt + context_section + output_format
    
    async def _execute_grok_analysis(self, prompt: str, budget: int) -> Dict[str, Any]:
        """
        Execute analysis using Grok-4-0709.
        
        Args:
            prompt: Formatted prompt for analysis
            budget: Token budget for this request
            
        Returns:
            Grok response with analysis results
        """
        try:
            response = await self.grok_client.chat.completions.create(
                model="grok-4-0709",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert smart contract security researcher and exploit developer. Provide detailed, technical analysis with actionable insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=min(budget, 4000),  # Respect budget constraints
                temperature=0.7,
                top_p=0.9
            )
            
            return {
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Grok-4-0709 analysis failed: {e}")
            raise
    
    async def _process_grok_response(self, grok_response: Dict[str, Any], phase: IterationPhase) -> Dict[str, Any]:
        """
        Process and structure the Grok-4-0709 response.
        
        Args:
            grok_response: Raw response from Grok
            phase: Current iteration phase
            
        Returns:
            Structured findings dictionary
        """
        try:
            content = grok_response['content']
            
            if content.strip().startswith('{'):
                findings = json.loads(content)
            else:
                import re
                json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    findings = json.loads(json_match.group(1))
                else:
                    findings = {
                        'phase': phase.value,
                        'raw_analysis': content,
                        'structured': False
                    }
            
            if 'confidence_score' not in findings:
                findings['confidence_score'] = 0.5  # Default confidence
            
            if 'findings' not in findings:
                findings['findings'] = {}
            
            return findings
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Grok response as JSON: {e}")
            return {
                'phase': phase.value,
                'raw_analysis': grok_response['content'],
                'structured': False,
                'confidence_score': 0.3
            }
    
    async def _update_strategies(self, findings: Dict[str, Any], phase: IterationPhase) -> List[Dict[str, Any]]:
        """
        Update exploit strategies based on new findings.
        
        Args:
            findings: Structured findings from current iteration
            phase: Current iteration phase
            
        Returns:
            List of strategy updates
        """
        strategy_updates = []
        
        if 'strategies' in findings:
            for strategy_data in findings['strategies']:
                strategy = ExploitStrategy(
                    strategy_id=strategy_data.get('strategy_id', f"strat_{int(time.time())}"),
                    target_contract=self.state.target_contract,
                    vulnerability_type=strategy_data.get('vulnerability_type', 'unknown'),
                    attack_vector=strategy_data.get('attack_vector', ''),
                    preconditions=strategy_data.get('preconditions', []),
                    execution_steps=strategy_data.get('execution_steps', []),
                    expected_profit_usd=strategy_data.get('expected_profit_usd', 0),
                    confidence_score=strategy_data.get('confidence_score', 0.5),
                    risk_assessment=strategy_data.get('risk_assessment', {}),
                    validation_status='pending',
                    created_at=int(time.time()),
                    updated_at=int(time.time())
                )
                
                existing_strategy = next(
                    (s for s in self.state.strategies_generated if s.strategy_id == strategy.strategy_id),
                    None
                )
                
                if existing_strategy:
                    existing_strategy.confidence_score = strategy.confidence_score
                    existing_strategy.expected_profit_usd = strategy.expected_profit_usd
                    existing_strategy.updated_at = strategy.updated_at
                    strategy_updates.append({'action': 'updated', 'strategy_id': strategy.strategy_id})
                else:
                    self.state.strategies_generated.append(strategy)
                    strategy_updates.append({'action': 'created', 'strategy_id': strategy.strategy_id})
        
        return strategy_updates
    
    def _calculate_confidence_score(self, findings: Dict[str, Any], iteration: int) -> float:
        """
        Calculate confidence score for the current iteration.
        
        Args:
            findings: Structured findings from current iteration
            iteration: Current iteration number
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = findings.get('confidence_score', 0.5)
        
        iteration_factor = min(iteration / self.max_iterations, 1.0)
        
        strategy_factor = 1.0
        if self.state.strategies_generated:
            avg_strategy_confidence = sum(s.confidence_score for s in self.state.strategies_generated) / len(self.state.strategies_generated)
            strategy_factor = avg_strategy_confidence
        
        findings_factor = 1.0
        if 'findings' in findings:
            findings_count = sum(len(v) if isinstance(v, list) else 1 for v in findings['findings'].values())
            findings_factor = min(findings_count / 10, 1.0)  # Normalize to 0-1
        
        confidence = (base_confidence * 0.4 + 
                     iteration_factor * 0.2 + 
                     strategy_factor * 0.3 + 
                     findings_factor * 0.1)
        
        return min(max(confidence, 0.0), 1.0)  # Clamp to 0-1 range
    
    def _should_terminate_early(self, iteration_results: List[IterationResult]) -> bool:
        """
        Determine if the analysis should terminate early.
        
        Args:
            iteration_results: Results from completed iterations
            
        Returns:
            True if early termination is recommended
        """
        if len(iteration_results) < 2:
            return False
        
        recent_confidences = [r.confidence_score for r in iteration_results[-2:]]
        if all(c > self.confidence_threshold for c in recent_confidences):
            confidence_improvement = recent_confidences[-1] - recent_confidences[-2]
            if confidence_improvement < 0.05:  # Less than 5% improvement
                logger.info("Early termination: confidence converged")
                return True
        
        if len(self.state.strategies_generated) > 0:
            high_confidence_strategies = [
                s for s in self.state.strategies_generated 
                if s.confidence_score > 0.8
            ]
            if len(high_confidence_strategies) >= 2:
                logger.info("Early termination: sufficient high-confidence strategies")
                return True
        
        if len(iteration_results) >= 3:
            recent_token_usage = [r.token_usage.get('total_tokens', 0) for r in iteration_results[-2:]]
            if all(usage > 0 for usage in recent_token_usage):
                efficiency_ratio = recent_confidences[-1] / recent_token_usage[-1]
                if efficiency_ratio < 0.0001:  # Low efficiency threshold
                    logger.info("Early termination: low budget efficiency")
                    return True
        
        return False
    
    async def _generate_final_analysis(self, iteration_results: List[IterationResult]) -> Dict[str, Any]:
        """
        Generate final analysis report from all iteration results.
        
        Args:
            iteration_results: Results from all completed iterations
            
        Returns:
            Comprehensive final analysis
        """
        final_analysis = {
            'session_summary': {
                'target_contract': self.state.target_contract,
                'total_iterations': len(iteration_results),
                'total_budget_used': self.state.total_budget_used,
                'session_duration': int(time.time()) - self.state.session_start_time,
                'final_confidence': self.state.confidence_progression[-1] if self.state.confidence_progression else 0.0
            },
            'iteration_progression': [
                {
                    'iteration': r.iteration_number,
                    'phase': r.phase.value,
                    'confidence': r.confidence_score,
                    'success': r.success,
                    'execution_time': r.execution_time
                }
                for r in iteration_results
            ],
            'generated_strategies': [
                {
                    'strategy_id': s.strategy_id,
                    'vulnerability_type': s.vulnerability_type,
                    'attack_vector': s.attack_vector,
                    'confidence_score': s.confidence_score,
                    'expected_profit_usd': s.expected_profit_usd,
                    'execution_steps': len(s.execution_steps),
                    'risk_level': self._assess_risk_level(s.risk_assessment)
                }
                for s in self.state.strategies_generated
            ],
            'key_findings': self._extract_key_findings(),
            'recommendations': self._generate_recommendations(),
            'profitability_assessment': self._assess_overall_profitability(),
            'risk_assessment': self._assess_overall_risk()
        }
        
        return final_analysis
    
    def _assess_risk_level(self, risk_assessment: Dict[str, Any]) -> str:
        """Assess overall risk level from risk assessment data."""
        if not risk_assessment:
            return 'unknown'
        
        risk_score = 0
        
        if risk_assessment.get('detection_probability', 0) > 0.7:
            risk_score += 3
        elif risk_assessment.get('detection_probability', 0) > 0.4:
            risk_score += 2
        else:
            risk_score += 1
        
        if risk_assessment.get('execution_complexity', 'medium') == 'high':
            risk_score += 2
        elif risk_assessment.get('execution_complexity', 'medium') == 'medium':
            risk_score += 1
        
        if risk_score >= 4:
            return 'high'
        elif risk_score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _extract_key_findings(self) -> List[str]:
        """Extract key findings from all iterations."""
        key_findings = []
        
        for findings in self.state.findings_history:
            if 'findings' in findings:
                findings_data = findings['findings']
                
                if 'vulnerabilities' in findings_data:
                    for vuln in findings_data['vulnerabilities']:
                        if isinstance(vuln, str):
                            key_findings.append(f"Vulnerability: {vuln}")
                        elif isinstance(vuln, dict):
                            key_findings.append(f"Vulnerability: {vuln.get('type', 'Unknown')} - {vuln.get('description', '')}")
                
                if 'attack_vectors' in findings_data:
                    for vector in findings_data['attack_vectors']:
                        if isinstance(vector, str):
                            key_findings.append(f"Attack Vector: {vector}")
        
        return list(set(key_findings))[:10]
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        
        if self.state.strategies_generated:
            high_confidence_strategies = [s for s in self.state.strategies_generated if s.confidence_score > 0.7]
            
            if high_confidence_strategies:
                best_strategy = max(high_confidence_strategies, key=lambda s: s.expected_profit_usd)
                recommendations.append(f"Recommended strategy: {best_strategy.vulnerability_type} with expected profit of ${best_strategy.expected_profit_usd:,.2f}")
            
            if len(self.state.strategies_generated) > 3:
                recommendations.append("Multiple exploit vectors identified - consider parallel execution")
        
        final_confidence = self.state.confidence_progression[-1] if self.state.confidence_progression else 0.0
        
        if final_confidence > 0.8:
            recommendations.append("High confidence analysis - proceed with exploit execution")
        elif final_confidence > 0.6:
            recommendations.append("Medium confidence - consider additional validation before execution")
        else:
            recommendations.append("Low confidence - recommend further analysis or alternative targets")
        
        if self.state.total_budget_used > self.base_budget_per_iteration * 3:
            recommendations.append("High token usage - optimize prompts for future analyses")
        
        return recommendations
    
    def _assess_overall_profitability(self) -> Dict[str, Any]:
        """Assess overall profitability of identified strategies."""
        if not self.state.strategies_generated:
            return {'assessment': 'no_strategies', 'total_potential': 0}
        
        total_potential = sum(s.expected_profit_usd for s in self.state.strategies_generated)
        avg_confidence = sum(s.confidence_score for s in self.state.strategies_generated) / len(self.state.strategies_generated)
        
        risk_adjusted_potential = total_potential * avg_confidence
        
        assessment = 'low'
        if risk_adjusted_potential > 10000:
            assessment = 'high'
        elif risk_adjusted_potential > 1000:
            assessment = 'medium'
        
        return {
            'assessment': assessment,
            'total_potential': total_potential,
            'risk_adjusted_potential': risk_adjusted_potential,
            'strategy_count': len(self.state.strategies_generated),
            'average_confidence': avg_confidence
        }
    
    def _assess_overall_risk(self) -> Dict[str, Any]:
        """Assess overall risk of the analysis and strategies."""
        if not self.state.strategies_generated:
            return {'level': 'unknown', 'factors': []}
        
        risk_factors = []
        risk_scores = []
        
        for strategy in self.state.strategies_generated:
            risk_level = self._assess_risk_level(strategy.risk_assessment)
            
            if risk_level == 'high':
                risk_scores.append(3)
                risk_factors.append(f"High-risk strategy: {strategy.vulnerability_type}")
            elif risk_level == 'medium':
                risk_scores.append(2)
            else:
                risk_scores.append(1)
        
        avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        overall_level = 'low'
        if avg_risk_score >= 2.5:
            overall_level = 'high'
        elif avg_risk_score >= 1.5:
            overall_level = 'medium'
        
        return {
            'level': overall_level,
            'average_score': avg_risk_score,
            'factors': risk_factors[:5]  # Top 5 risk factors
        }
    
    async def get_session_status(self) -> Dict[str, Any]:
        """Get current session status and progress."""
        if not self.state:
            return {'status': 'not_initialized'}
        
        return {
            'status': 'active',
            'current_iteration': self.state.current_iteration,
            'current_phase': self.state.current_phase.value,
            'target_contract': self.state.target_contract,
            'budget_used': self.state.total_budget_used,
            'strategies_count': len(self.state.strategies_generated),
            'confidence_progression': self.state.confidence_progression,
            'session_duration': int(time.time()) - self.state.session_start_time
        }
    
    async def cleanup_session(self):
        """Clean up session resources."""
        if self.state:
            execution_tool = self.tools.get('concrete_execution')
            if execution_tool:
                pass
            
            logger.info(f"Cleaned up session for {self.state.target_contract}")
            self.state = None
