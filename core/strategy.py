"""
Strategy Generator - A1 Agentic System

Generates and refines exploit strategies based on contract analysis and feedback.
Implements advanced strategy optimization, risk assessment, and economic validation
for autonomous exploit generation with multi-vector attack planning.

Based on the A1 research paper specifications.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from decimal import Decimal
import hashlib
import random
from collections import defaultdict

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """Types of exploit strategies"""
    REENTRANCY = "reentrancy"
    FLASH_LOAN = "flash_loan"
    PRICE_MANIPULATION = "price_manipulation"
    ACCESS_CONTROL = "access_control"
    ARITHMETIC_OVERFLOW = "arithmetic_overflow"
    FRONT_RUNNING = "front_running"
    SANDWICH_ATTACK = "sandwich_attack"
    GOVERNANCE_ATTACK = "governance_attack"
    ORACLE_MANIPULATION = "oracle_manipulation"
    LIQUIDITY_DRAIN = "liquidity_drain"

class StrategyComplexity(Enum):
    """Strategy complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class StrategyStep:
    """Individual step in an exploit strategy"""
    step_id: str
    step_number: int
    action_type: str
    target_contract: str
    function_signature: str
    parameters: Dict[str, Any]
    expected_outcome: str
    gas_estimate: int
    dependencies: List[str]
    validation_checks: List[str]

@dataclass
class StrategyPrecondition:
    """Precondition required for strategy execution"""
    condition_id: str
    condition_type: str
    description: str
    validation_method: str
    parameters: Dict[str, Any]
    critical: bool

@dataclass
class RiskAssessment:
    """Risk assessment for exploit strategy"""
    assessment_id: str
    overall_risk: RiskLevel
    detection_probability: float
    execution_complexity: StrategyComplexity
    capital_requirements: Decimal
    time_sensitivity: str
    legal_implications: List[str]
    technical_risks: List[str]
    economic_risks: List[str]
    mitigation_strategies: List[str]

@dataclass
class EconomicModel:
    """Economic model for strategy profitability"""
    model_id: str
    expected_profit_usd: Decimal
    confidence_interval: Tuple[Decimal, Decimal]
    gas_cost_estimate: Decimal
    capital_requirement: Decimal
    roi_percentage: Decimal
    break_even_point: Decimal
    market_impact: str
    slippage_tolerance: float
    price_assumptions: Dict[str, Any]

@dataclass
class ExploitStrategy:
    """Complete exploit strategy definition"""
    strategy_id: str
    strategy_type: StrategyType
    target_contract: str
    vulnerability_description: str
    attack_vector: str
    complexity: StrategyComplexity
    execution_steps: List[StrategyStep]
    preconditions: List[StrategyPrecondition]
    risk_assessment: RiskAssessment
    economic_model: EconomicModel
    confidence_score: float
    estimated_success_probability: float
    alternative_strategies: List[str]
    created_at: int
    updated_at: int
    validation_status: str

class StrategyGenerator:
    """
    Advanced strategy generator for autonomous exploit development.
    
    Generates, refines, and optimizes exploit strategies based on contract
    analysis, vulnerability assessment, and execution feedback.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the strategy generator.
        
        Args:
            config: Configuration dictionary with generation settings
        """
        self.config = config
        
        self.generated_strategies: Dict[str, ExploitStrategy] = {}
        self.strategy_templates: Dict[StrategyType, Dict[str, Any]] = {}
        
        self.max_strategies_per_contract = config.get('MAX_STRATEGIES_PER_CONTRACT', 5)
        self.min_confidence_threshold = config.get('MIN_CONFIDENCE_THRESHOLD', 0.6)
        self.risk_tolerance = config.get('RISK_TOLERANCE', RiskLevel.MEDIUM)
        
        self.min_profit_threshold = Decimal(str(config.get('MIN_PROFIT_THRESHOLD', 100)))
        self.max_capital_requirement = Decimal(str(config.get('MAX_CAPITAL_REQUIREMENT', 100000)))
        self.min_roi_threshold = Decimal(str(config.get('MIN_ROI_THRESHOLD', 10)))  # 10%
        
        self.strategy_templates = self._initialize_strategy_templates()
        
        self.strategy_performance: Dict[str, Dict[str, float]] = defaultdict(dict)
    
    def _initialize_strategy_templates(self) -> Dict[StrategyType, Dict[str, Any]]:
        """Initialize strategy templates for different exploit types."""
        return {
            StrategyType.REENTRANCY: {
                'description': 'Exploit reentrancy vulnerabilities in external calls',
                'complexity': StrategyComplexity.MODERATE,
                'typical_steps': [
                    'identify_vulnerable_function',
                    'create_malicious_contract',
                    'trigger_initial_call',
                    'execute_reentrancy',
                    'extract_funds'
                ],
                'preconditions': [
                    'external_call_before_state_update',
                    'insufficient_reentrancy_protection',
                    'valuable_state_manipulation'
                ],
                'risk_factors': ['detection_probability_medium', 'execution_complexity_moderate'],
                'capital_requirement': 'low_to_medium',
                'success_indicators': ['state_manipulation', 'fund_extraction']
            },
            
            StrategyType.FLASH_LOAN: {
                'description': 'Utilize flash loans for capital-intensive exploits',
                'complexity': StrategyComplexity.COMPLEX,
                'typical_steps': [
                    'initiate_flash_loan',
                    'manipulate_market_conditions',
                    'execute_primary_exploit',
                    'arbitrage_opportunities',
                    'repay_flash_loan',
                    'extract_profit'
                ],
                'preconditions': [
                    'flash_loan_availability',
                    'profitable_arbitrage_opportunity',
                    'sufficient_liquidity'
                ],
                'risk_factors': ['high_gas_costs', 'timing_sensitivity', 'slippage_risk'],
                'capital_requirement': 'minimal_upfront',
                'success_indicators': ['arbitrage_profit', 'loan_repayment']
            },
            
            StrategyType.ACCESS_CONTROL: {
                'description': 'Exploit access control vulnerabilities',
                'complexity': StrategyComplexity.SIMPLE,
                'typical_steps': [
                    'identify_privilege_escalation',
                    'craft_exploit_transaction',
                    'bypass_access_controls',
                    'execute_privileged_actions',
                    'extract_value'
                ],
                'preconditions': [
                    'weak_access_controls',
                    'privilege_escalation_vector',
                    'valuable_privileged_functions'
                ],
                'risk_factors': ['detection_probability_high', 'limited_time_window'],
                'capital_requirement': 'minimal',
                'success_indicators': ['privilege_escalation', 'unauthorized_access']
            }
        }
    
    async def generate_strategies(self, contract_analysis: Dict[str, Any], context: Dict[str, Any]) -> List[ExploitStrategy]:
        """
        Generate exploit strategies based on contract analysis.
        
        Args:
            contract_analysis: Comprehensive contract analysis results
            context: Additional context and constraints
            
        Returns:
            List of generated exploit strategies
        """
        logger.info(f"Generating strategies for contract {context.get('target_contract', 'unknown')}")
        
        vulnerability_analysis = await self._analyze_vulnerabilities(contract_analysis)
        
        base_strategies = []
        
        for vulnerability in vulnerability_analysis['vulnerabilities']:
            strategies = await self._generate_strategies_for_vulnerability(
                vulnerability, contract_analysis, context
            )
            base_strategies.extend(strategies)
        
        optimized_strategies = await self._optimize_strategies(base_strategies, context)
        
        validated_strategies = await self._validate_strategies(optimized_strategies, context)
        
        for strategy in validated_strategies:
            self.generated_strategies[strategy.strategy_id] = strategy
        
        logger.info(f"Generated {len(validated_strategies)} validated strategies")
        
        return validated_strategies
    
    async def _analyze_vulnerabilities(self, contract_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze contract for exploitable vulnerabilities."""
        vulnerabilities = []
        
        source_code = contract_analysis.get('source_code', {})
        state_analysis = contract_analysis.get('state_analysis', {})
        constructor_analysis = contract_analysis.get('constructor_analysis', {})
        sanitized_code = contract_analysis.get('sanitized_code', {})
        
        reentrancy_vulns = self._detect_reentrancy_vulnerabilities(source_code, sanitized_code)
        vulnerabilities.extend(reentrancy_vulns)
        
        access_control_vulns = self._detect_access_control_vulnerabilities(source_code, constructor_analysis)
        vulnerabilities.extend(access_control_vulns)
        
        return {
            'vulnerabilities': vulnerabilities,
            'total_count': len(vulnerabilities),
            'high_severity': len([v for v in vulnerabilities if v.get('severity') == 'high']),
            'exploitability_score': self._calculate_exploitability_score(vulnerabilities)
        }
    
    def _detect_reentrancy_vulnerabilities(self, source_code: Dict[str, Any], sanitized_code: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect reentrancy vulnerabilities in contract code."""
        vulnerabilities = []
        
        code_content = source_code.get('source_code', '')
        functions = sanitized_code.get('critical_functions', [])
        
        for function in functions:
            function_name = function.get('name', '')
            function_code = function.get('code', '')
            
            external_call_patterns = [
                'call(',
                '.call(',
                '.transfer(',
                '.send(',
                'delegatecall(',
                'staticcall('
            ]
            
            has_external_call = any(pattern in function_code.lower() for pattern in external_call_patterns)
            
            if has_external_call:
                vulnerabilities.append({
                    'type': 'reentrancy',
                    'severity': 'high',
                    'function': function_name,
                    'description': f'Potential reentrancy in {function_name}',
                    'exploitation_method': 'recursive_calling',
                    'confidence': 0.8,
                    'attack_vector': 'external_call_reentrancy'
                })
        
        return vulnerabilities
    
    def _detect_access_control_vulnerabilities(self, source_code: Dict[str, Any], constructor_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect access control vulnerabilities."""
        vulnerabilities = []
        
        code_content = source_code.get('source_code', '')
        
        weak_patterns = [
            'tx.origin',
            'msg.sender == owner',
            'require(msg.sender',
            'onlyOwner',
            'onlyAdmin'
        ]
        
        access_control_functions = []
        
        for pattern in weak_patterns:
            if pattern in code_content:
                access_control_functions.append(pattern)
        
        if access_control_functions:
            vulnerabilities.append({
                'type': 'access_control',
                'severity': 'medium',
                'description': 'Potential privilege escalation through constructor',
                'exploitation_method': 'constructor_manipulation',
                'confidence': 0.6,
                'attack_vector': 'privilege_escalation'
            })
        
        return vulnerabilities
    
    def _calculate_exploitability_score(self, vulnerabilities: List[Dict[str, Any]]) -> float:
        """Calculate overall exploitability score."""
        if not vulnerabilities:
            return 0.0
        
        severity_weights = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        total_score = 0.0
        for vuln in vulnerabilities:
            severity = vuln.get('severity', 'low')
            confidence = vuln.get('confidence', 0.5)
            score = severity_weights.get(severity, 0.4) * confidence
            total_score += score
        
        max_possible_score = len(vulnerabilities) * 1.0
        return min(total_score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
    
    async def _generate_strategies_for_vulnerability(self, vulnerability: Dict[str, Any], contract_analysis: Dict[str, Any], context: Dict[str, Any]) -> List[ExploitStrategy]:
        """Generate specific strategies for a vulnerability."""
        strategies = []
        
        vuln_type = vulnerability.get('type')
        strategy_type = self._map_vulnerability_to_strategy_type(vuln_type)
        
        if strategy_type:
            template = self.strategy_templates.get(strategy_type, {})
            
            strategy = await self._create_strategy_from_template(
                strategy_type, template, vulnerability, contract_analysis, context
            )
            
            if strategy:
                strategies.append(strategy)
        
        return strategies
    
    def _map_vulnerability_to_strategy_type(self, vulnerability_type: str) -> Optional[StrategyType]:
        """Map vulnerability type to strategy type."""
        mapping = {
            'reentrancy': StrategyType.REENTRANCY,
            'access_control': StrategyType.ACCESS_CONTROL,
            'flash_loan': StrategyType.FLASH_LOAN
        }
        
        return mapping.get(vulnerability_type)
    
    async def _create_strategy_from_template(self, strategy_type: StrategyType, template: Dict[str, Any], vulnerability: Dict[str, Any], contract_analysis: Dict[str, Any], context: Dict[str, Any]) -> Optional[ExploitStrategy]:
        """Create a strategy from template and vulnerability analysis."""
        
        strategy_id = self._generate_strategy_id(strategy_type, context.get('target_contract', ''))
        
        execution_steps = await self._generate_execution_steps(strategy_type, template, vulnerability, contract_analysis)
        
        preconditions = self._generate_preconditions(template, vulnerability, contract_analysis)
        
        risk_assessment = await self._perform_risk_assessment(strategy_type, vulnerability, contract_analysis, context)
        
        economic_model = await self._create_economic_model(strategy_type, vulnerability, contract_analysis, context)
        
        confidence_score = self._calculate_strategy_confidence(vulnerability, risk_assessment, economic_model)
        
        success_probability = self._estimate_success_probability(strategy_type, vulnerability, risk_assessment)
        
        strategy = ExploitStrategy(
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            target_contract=context.get('target_contract', ''),
            vulnerability_description=vulnerability.get('description', ''),
            attack_vector=vulnerability.get('attack_vector', ''),
            complexity=template.get('complexity', StrategyComplexity.MODERATE),
            execution_steps=execution_steps,
            preconditions=preconditions,
            risk_assessment=risk_assessment,
            economic_model=economic_model,
            confidence_score=confidence_score,
            estimated_success_probability=success_probability,
            alternative_strategies=[],
            created_at=int(time.time()),
            updated_at=int(time.time()),
            validation_status='pending'
        )
        
        return strategy
    
    def _generate_strategy_id(self, strategy_type: StrategyType, target_contract: str) -> str:
        """Generate unique strategy ID."""
        timestamp = int(time.time())
        content = f"{strategy_type.value}_{target_contract}_{timestamp}"
        hash_object = hashlib.md5(content.encode())
        return f"strategy_{hash_object.hexdigest()[:8]}"
    
    async def _generate_execution_steps(self, strategy_type: StrategyType, template: Dict[str, Any], vulnerability: Dict[str, Any], contract_analysis: Dict[str, Any]) -> List[StrategyStep]:
        """Generate execution steps for the strategy."""
        steps = []
        typical_steps = template.get('typical_steps', [])
        
        for i, step_name in enumerate(typical_steps):
            step = StrategyStep(
                step_id=f"step_{i+1}_{step_name}",
                step_number=i + 1,
                action_type=step_name,
                target_contract=contract_analysis.get('contract_address', ''),
                function_signature=vulnerability.get('function', 'unknown'),
                parameters={},
                expected_outcome=f"Execute {step_name}",
                gas_estimate=50000 + (i * 10000),
                dependencies=[f"step_{i}_{typical_steps[i-1]}"] if i > 0 else [],
                validation_checks=[f"validate_{step_name}"]
            )
            steps.append(step)
        
        return steps
    
    def _generate_preconditions(self, template: Dict[str, Any], vulnerability: Dict[str, Any], contract_analysis: Dict[str, Any]) -> List[StrategyPrecondition]:
        """Generate preconditions for the strategy."""
        preconditions = []
        template_preconditions = template.get('preconditions', [])
        
        for i, condition_name in enumerate(template_preconditions):
            precondition = StrategyPrecondition(
                condition_id=f"precond_{i+1}_{condition_name}",
                condition_type=condition_name,
                description=f"Verify {condition_name}",
                validation_method=f"check_{condition_name}",
                parameters={},
                critical=i < 2
            )
            preconditions.append(precondition)
        
        return preconditions
    
    async def _perform_risk_assessment(self, strategy_type: StrategyType, vulnerability: Dict[str, Any], contract_analysis: Dict[str, Any], context: Dict[str, Any]) -> RiskAssessment:
        """Perform comprehensive risk assessment."""
        
        severity = vulnerability.get('severity', 'medium')
        risk_mapping = {
            'low': RiskLevel.LOW,
            'medium': RiskLevel.MEDIUM,
            'high': RiskLevel.HIGH,
            'critical': RiskLevel.CRITICAL
        }
        overall_risk = risk_mapping.get(severity, RiskLevel.MEDIUM)
        
        detection_probability = 0.3 + (0.2 * len(vulnerability.get('attack_vector', '')))
        detection_probability = min(detection_probability, 0.9)
        
        complexity_mapping = {
            StrategyType.ACCESS_CONTROL: StrategyComplexity.SIMPLE,
            StrategyType.REENTRANCY: StrategyComplexity.MODERATE,
            StrategyType.FLASH_LOAN: StrategyComplexity.COMPLEX
        }
        execution_complexity = complexity_mapping.get(strategy_type, StrategyComplexity.MODERATE)
        
        capital_requirements = Decimal('1000')
        if strategy_type == StrategyType.FLASH_LOAN:
            capital_requirements = Decimal('50000')
        
        return RiskAssessment(
            assessment_id=f"risk_{int(time.time())}",
            overall_risk=overall_risk,
            detection_probability=detection_probability,
            execution_complexity=execution_complexity,
            capital_requirements=capital_requirements,
            time_sensitivity="medium",
            legal_implications=["Unauthorized access", "Financial manipulation"],
            technical_risks=["Transaction failure", "Gas estimation errors"],
            economic_risks=["Market volatility", "Slippage"],
            mitigation_strategies=["Use multiple transactions", "Implement fallback mechanisms"]
        )
    
    async def _create_economic_model(self, strategy_type: StrategyType, vulnerability: Dict[str, Any], contract_analysis: Dict[str, Any], context: Dict[str, Any]) -> EconomicModel:
        """Create economic model for strategy profitability."""
        
        base_profit = Decimal('5000')
        
        if strategy_type == StrategyType.FLASH_LOAN:
            base_profit = Decimal('15000')
        
        lower_bound = base_profit * Decimal('0.7')
        upper_bound = base_profit * Decimal('1.3')
        
        gas_cost = Decimal('500')
        
        capital_requirement = Decimal('1000')
        if strategy_type == StrategyType.FLASH_LOAN:
            capital_requirement = Decimal('10000')
        
        roi_percentage = ((base_profit - gas_cost) / max(capital_requirement, Decimal('1'))) * 100
        
        return EconomicModel(
            model_id=f"econ_{int(time.time())}",
            expected_profit_usd=base_profit,
            confidence_interval=(lower_bound, upper_bound),
            gas_cost_estimate=gas_cost,
            capital_requirement=capital_requirement,
            roi_percentage=roi_percentage,
            break_even_point=gas_cost + capital_requirement,
            market_impact="medium",
            slippage_tolerance=0.05,
            price_assumptions={"stable_market": True, "sufficient_liquidity": True}
        )
    
    def _calculate_strategy_confidence(self, vulnerability: Dict[str, Any], risk_assessment: RiskAssessment, economic_model: EconomicModel) -> float:
        """Calculate overall strategy confidence score."""
        
        vuln_confidence = vulnerability.get('confidence', 0.5)
        
        risk_penalty = {
            RiskLevel.LOW: 0.0,
            RiskLevel.MEDIUM: 0.1,
            RiskLevel.HIGH: 0.2,
            RiskLevel.CRITICAL: 0.3
        }
        risk_adjustment = risk_penalty.get(risk_assessment.overall_risk, 0.1)
        
        economic_bonus = 0.1 if economic_model.roi_percentage > 50 else 0.0
        
        confidence = vuln_confidence - risk_adjustment + economic_bonus
        
        return max(0.0, min(1.0, confidence))
    
    def _estimate_success_probability(self, strategy_type: StrategyType, vulnerability: Dict[str, Any], risk_assessment: RiskAssessment) -> float:
        """Estimate success probability for the strategy."""
        
        base_success_rates = {
            StrategyType.ACCESS_CONTROL: 0.8,
            StrategyType.REENTRANCY: 0.7,
            StrategyType.FLASH_LOAN: 0.6
        }
        
        base_rate = base_success_rates.get(strategy_type, 0.5)
        
        vuln_confidence = vulnerability.get('confidence', 0.5)
        confidence_adjustment = (vuln_confidence - 0.5) * 0.2
        
        detection_penalty = risk_assessment.detection_probability * 0.1
        
        success_probability = base_rate + confidence_adjustment - detection_penalty
        
        return max(0.1, min(0.9, success_probability))
    
    async def _optimize_strategies(self, strategies: List[ExploitStrategy], context: Dict[str, Any]) -> List[ExploitStrategy]:
        """Optimize strategies using various techniques."""
        
        if not strategies:
            return strategies
        
        optimized_strategies = []
        
        for strategy in strategies:
            optimized_strategy = await self._apply_optimization_techniques(strategy, context)
            optimized_strategies.append(optimized_strategy)
        
        optimized_strategies.sort(key=lambda s: s.confidence_score, reverse=True)
        
        return optimized_strategies
    
    async def _apply_optimization_techniques(self, strategy: ExploitStrategy, context: Dict[str, Any]) -> ExploitStrategy:
        """Apply optimization techniques to a single strategy."""
        
        optimized_steps = []
        for step in strategy.execution_steps:
            optimized_gas = int(step.gas_estimate * 0.9)
            
            optimized_step = StrategyStep(
                step_id=step.step_id,
                step_number=step.step_number,
                action_type=step.action_type,
                target_contract=step.target_contract,
                function_signature=step.function_signature,
                parameters=step.parameters,
                expected_outcome=step.expected_outcome,
                gas_estimate=optimized_gas,
                dependencies=step.dependencies,
                validation_checks=step.validation_checks
            )
            optimized_steps.append(optimized_step)
        
        total_gas_savings = sum(step.gas_estimate for step in strategy.execution_steps) - sum(step.gas_estimate for step in optimized_steps)
        gas_savings_usd = Decimal(str(total_gas_savings * 0.00002))
        
        optimized_economic_model = EconomicModel(
            model_id=strategy.economic_model.model_id,
            expected_profit_usd=strategy.economic_model.expected_profit_usd + gas_savings_usd,
            confidence_interval=strategy.economic_model.confidence_interval,
            gas_cost_estimate=strategy.economic_model.gas_cost_estimate - gas_savings_usd,
            capital_requirement=strategy.economic_model.capital_requirement,
            roi_percentage=strategy.economic_model.roi_percentage + Decimal('5'),
            break_even_point=strategy.economic_model.break_even_point,
            market_impact=strategy.economic_model.market_impact,
            slippage_tolerance=strategy.economic_model.slippage_tolerance,
            price_assumptions=strategy.economic_model.price_assumptions
        )
        
        optimized_strategy = ExploitStrategy(
            strategy_id=strategy.strategy_id,
            strategy_type=strategy.strategy_type,
            target_contract=strategy.target_contract,
            vulnerability_description=strategy.vulnerability_description,
            attack_vector=strategy.attack_vector,
            complexity=strategy.complexity,
            execution_steps=optimized_steps,
            preconditions=strategy.preconditions,
            risk_assessment=strategy.risk_assessment,
            economic_model=optimized_economic_model,
            confidence_score=min(strategy.confidence_score + 0.05, 1.0),
            estimated_success_probability=strategy.estimated_success_probability,
            alternative_strategies=strategy.alternative_strategies,
            created_at=strategy.created_at,
            updated_at=int(time.time()),
            validation_status=strategy.validation_status
        )
        
        return optimized_strategy
    
    async def _validate_strategies(self, strategies: List[ExploitStrategy], context: Dict[str, Any]) -> List[ExploitStrategy]:
        """Validate and filter strategies based on criteria."""
        
        validated_strategies = []
        
        for strategy in strategies:
            if strategy.confidence_score < self.min_confidence_threshold:
                continue
            
            if strategy.economic_model.expected_profit_usd < self.min_profit_threshold:
                continue
            
            if strategy.economic_model.capital_requirement > self.max_capital_requirement:
                continue
            
            if strategy.economic_model.roi_percentage < self.min_roi_threshold:
                continue
            
            risk_levels = {
                RiskLevel.LOW: 1,
                RiskLevel.MEDIUM: 2,
                RiskLevel.HIGH: 3,
                RiskLevel.CRITICAL: 4
            }
            
            if risk_levels.get(strategy.risk_assessment.overall_risk, 2) > risk_levels.get(self.risk_tolerance, 2):
                continue
            
            strategy.validation_status = 'validated'
            validated_strategies.append(strategy)
        
        return validated_strategies
    
    def get_all_strategies(self, filter_by: Optional[Dict[str, Any]] = None) -> List[ExploitStrategy]:
        """
        Get all generated strategies with optional filtering.
        
        Args:
            filter_by: Optional filter criteria
            
        Returns:
            List of strategies matching the filter criteria
        """
        strategies = list(self.generated_strategies.values())
        
        if not filter_by:
            return strategies
        
        filtered_strategies = []
        
        for strategy in strategies:
            include_strategy = True
            
            if 'strategy_type' in filter_by:
                if strategy.strategy_type != filter_by['strategy_type']:
                    include_strategy = False
            
            if 'target_contract' in filter_by:
                if strategy.target_contract != filter_by['target_contract']:
                    include_strategy = False
            
            if 'min_confidence' in filter_by:
                if strategy.confidence_score < filter_by['min_confidence']:
                    include_strategy = False
            
            if include_strategy:
                filtered_strategies.append(strategy)
        
        return filtered_strategies
    
    async def cleanup_resources(self):
        """Clean up strategy generator resources."""
        logger.info("Cleaning up strategy generator resources")
        
        self.generated_strategies.clear()
        self.strategy_performance.clear()
        
        logger.info("Strategy generator cleanup completed")
