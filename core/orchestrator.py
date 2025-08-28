"""
Tool Orchestrator - A1 Agentic System

Handles autonomous tool selection and workflow management for the A1 agent.
Implements intelligent tool routing, parallel execution, and resource optimization
based on contract analysis context and iteration phase requirements.

Based on the A1 research paper specifications.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from collections import defaultdict

from monitoring.metrics import record_error, record_heartbeat, set_queue_depth

logger = logging.getLogger(__name__)

class ToolPriority(Enum):
    """Tool execution priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"

class ExecutionMode(Enum):
    """Tool execution modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ADAPTIVE = "adaptive"

@dataclass
class ToolExecution:
    """Container for tool execution information"""
    tool_name: str
    method_name: str
    parameters: Dict[str, Any]
    priority: ToolPriority
    execution_mode: ExecutionMode
    dependencies: List[str]
    timeout: int
    retry_count: int
    estimated_cost: int
    expected_output_type: str

@dataclass
class ExecutionResult:
    """Container for tool execution results"""
    tool_name: str
    method_name: str
    success: bool
    result: Any
    execution_time: float
    resource_usage: Dict[str, Any]
    error_message: Optional[str] = None
    retry_attempts: int = 0

@dataclass
class WorkflowPlan:
    """Container for workflow execution plan"""
    plan_id: str
    target_contract: str
    iteration_phase: str
    tool_executions: List[ToolExecution]
    estimated_total_cost: int
    estimated_duration: float
    parallel_groups: List[List[str]]
    dependency_graph: Dict[str, List[str]]

class ToolOrchestrator:
    """
    Intelligent tool orchestrator for autonomous workflow management.
    
    Handles tool selection, execution planning, resource optimization,
    and adaptive workflow management based on contract analysis context.
    """
    
    def __init__(self, tools: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialize the tool orchestrator.
        
        Args:
            tools: Dictionary of available domain-specific tools
            config: Configuration dictionary with orchestration settings
        """
        self.tools = tools
        self.config = config
        
        self.max_parallel_executions = config.get('MAX_PARALLEL_EXECUTIONS', 3)
        self.default_timeout = config.get('DEFAULT_TOOL_TIMEOUT', 300)  # 5 minutes
        self.max_retries = config.get('MAX_TOOL_RETRIES', 2)
        self.resource_budget = config.get('RESOURCE_BUDGET_PER_ITERATION', 1000)

        self.watchdog_restart_limit = config.get('WATCHDOG_RESTART_LIMIT', 1)
        self.watchdog_escalate_threshold = config.get('WATCHDOG_ESCALATE_THRESHOLD', 3)
        self.tool_failure_counts = defaultdict(int)
        
        self.tool_metadata = self._initialize_tool_metadata()
        
        self.execution_history: List[ExecutionResult] = []
        self.performance_metrics: Dict[str, Dict[str, float]] = {}
        
        self.tool_success_rates: Dict[str, float] = {}
        self.tool_avg_execution_times: Dict[str, float] = {}
        self.tool_cost_effectiveness: Dict[str, float] = {}
        
        self.workflow_templates = self._initialize_workflow_templates()
        
        self.executor = ThreadPoolExecutor(max_workers=self.max_parallel_executions)
    
    def _initialize_tool_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Initialize metadata for all available tools."""
        return {
            'source_code_fetcher': {
                'capabilities': ['source_code_retrieval', 'proxy_detection', 'abi_extraction'],
                'input_types': ['contract_address', 'chain_id'],
                'output_types': ['source_code', 'contract_info', 'proxy_info'],
                'estimated_cost': 50,
                'avg_execution_time': 5.0,
                'dependencies': [],
                'parallel_safe': True,
                'cache_duration': 3600,  # 1 hour
                'priority_by_phase': {
                    'reconnaissance': ToolPriority.CRITICAL,
                    'analysis': ToolPriority.HIGH,
                    'strategy_generation': ToolPriority.MEDIUM,
                    'execution_planning': ToolPriority.LOW,
                    'validation': ToolPriority.LOW
                }
            },
            'constructor_parameter': {
                'capabilities': ['deployment_analysis', 'parameter_decoding', 'configuration_analysis'],
                'input_types': ['contract_address', 'deployment_tx'],
                'output_types': ['constructor_params', 'deployment_info'],
                'estimated_cost': 30,
                'avg_execution_time': 3.0,
                'dependencies': [],
                'parallel_safe': True,
                'cache_duration': 7200,  # 2 hours
                'priority_by_phase': {
                    'reconnaissance': ToolPriority.HIGH,
                    'analysis': ToolPriority.MEDIUM,
                    'strategy_generation': ToolPriority.LOW,
                    'execution_planning': ToolPriority.LOW,
                    'validation': ToolPriority.LOW
                }
            },
            'state_reader': {
                'capabilities': ['state_capture', 'view_function_analysis', 'balance_tracking'],
                'input_types': ['contract_address', 'abi', 'block_number'],
                'output_types': ['state_snapshot', 'function_results'],
                'estimated_cost': 40,
                'avg_execution_time': 4.0,
                'dependencies': ['source_code_fetcher'],  # Needs ABI
                'parallel_safe': True,
                'cache_duration': 300,  # 5 minutes (state changes frequently)
                'priority_by_phase': {
                    'reconnaissance': ToolPriority.MEDIUM,
                    'analysis': ToolPriority.CRITICAL,
                    'strategy_generation': ToolPriority.HIGH,
                    'execution_planning': ToolPriority.MEDIUM,
                    'validation': ToolPriority.HIGH
                }
            },
            'code_sanitizer': {
                'capabilities': ['code_cleaning', 'complexity_analysis', 'function_extraction'],
                'input_types': ['source_code'],
                'output_types': ['sanitized_code', 'complexity_metrics'],
                'estimated_cost': 20,
                'avg_execution_time': 2.0,
                'dependencies': ['source_code_fetcher'],
                'parallel_safe': True,
                'cache_duration': 3600,  # 1 hour
                'priority_by_phase': {
                    'reconnaissance': ToolPriority.LOW,
                    'analysis': ToolPriority.HIGH,
                    'strategy_generation': ToolPriority.MEDIUM,
                    'execution_planning': ToolPriority.LOW,
                    'validation': ToolPriority.LOW
                }
            },
            'concrete_execution': {
                'capabilities': ['simulation', 'testing', 'trace_analysis'],
                'input_types': ['exploit_strategy', 'test_parameters'],
                'output_types': ['execution_results', 'traces', 'gas_analysis'],
                'estimated_cost': 100,
                'avg_execution_time': 15.0,
                'dependencies': ['source_code_fetcher', 'state_reader'],
                'parallel_safe': False,  # Blockchain fork conflicts
                'cache_duration': 600,  # 10 minutes
                'priority_by_phase': {
                    'reconnaissance': ToolPriority.OPTIONAL,
                    'analysis': ToolPriority.LOW,
                    'strategy_generation': ToolPriority.MEDIUM,
                    'execution_planning': ToolPriority.CRITICAL,
                    'validation': ToolPriority.CRITICAL
                }
            },
            'revenue_normalizer': {
                'capabilities': ['profit_analysis', 'token_valuation', 'economic_validation'],
                'input_types': ['balance_snapshots', 'token_addresses'],
                'output_types': ['profitability_analysis', 'economic_metrics'],
                'estimated_cost': 60,
                'avg_execution_time': 8.0,
                'dependencies': ['state_reader'],
                'parallel_safe': True,
                'cache_duration': 900,  # 15 minutes
                'priority_by_phase': {
                    'reconnaissance': ToolPriority.OPTIONAL,
                    'analysis': ToolPriority.MEDIUM,
                    'strategy_generation': ToolPriority.HIGH,
                    'execution_planning': ToolPriority.HIGH,
                    'validation': ToolPriority.CRITICAL
                }
            }
        }
    
    def _initialize_workflow_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize workflow templates for different iteration phases."""
        return {
            'reconnaissance': [
                {
                    'tool': 'source_code_fetcher',
                    'method': 'fetch_contract_source',
                    'priority': 'critical',
                    'parallel_group': 1
                },
                {
                    'tool': 'constructor_parameter',
                    'method': 'analyze_constructor_parameters',
                    'priority': 'high',
                    'parallel_group': 1
                },
                {
                    'tool': 'state_reader',
                    'method': 'capture_state_snapshot',
                    'priority': 'medium',
                    'parallel_group': 2,
                    'depends_on': ['source_code_fetcher']
                }
            ],
            'analysis': [
                {
                    'tool': 'code_sanitizer',
                    'method': 'sanitize_contract_code',
                    'priority': 'high',
                    'parallel_group': 1,
                    'depends_on': ['source_code_fetcher']
                },
                {
                    'tool': 'state_reader',
                    'method': 'analyze_view_functions',
                    'priority': 'critical',
                    'parallel_group': 1,
                    'depends_on': ['source_code_fetcher']
                },
                {
                    'tool': 'revenue_normalizer',
                    'method': 'capture_balance_snapshot',
                    'priority': 'medium',
                    'parallel_group': 2,
                    'depends_on': ['state_reader']
                }
            ],
            'strategy_generation': [
                {
                    'tool': 'state_reader',
                    'method': 'compare_state_snapshots',
                    'priority': 'high',
                    'parallel_group': 1
                },
                {
                    'tool': 'revenue_normalizer',
                    'method': 'analyze_exploit_profitability',
                    'priority': 'high',
                    'parallel_group': 1
                },
                {
                    'tool': 'concrete_execution',
                    'method': 'create_blockchain_fork',
                    'priority': 'medium',
                    'parallel_group': 2
                }
            ],
            'execution_planning': [
                {
                    'tool': 'concrete_execution',
                    'method': 'setup_forge_project',
                    'priority': 'critical',
                    'parallel_group': 1
                },
                {
                    'tool': 'concrete_execution',
                    'method': 'generate_test_file',
                    'priority': 'critical',
                    'parallel_group': 2,
                    'depends_on': ['setup_forge_project']
                },
                {
                    'tool': 'revenue_normalizer',
                    'method': 'validate_economic_assumptions',
                    'priority': 'high',
                    'parallel_group': 2
                }
            ],
            'validation': [
                {
                    'tool': 'concrete_execution',
                    'method': 'execute_exploit_test',
                    'priority': 'critical',
                    'parallel_group': 1
                },
                {
                    'tool': 'revenue_normalizer',
                    'method': 'calculate_profit_loss',
                    'priority': 'critical',
                    'parallel_group': 2,
                    'depends_on': ['execute_exploit_test']
                },
                {
                    'tool': 'revenue_normalizer',
                    'method': 'generate_profitability_report',
                    'priority': 'high',
                    'parallel_group': 3,
                    'depends_on': ['calculate_profit_loss']
                }
            ]
        }
    
    async def create_workflow_plan(self, target_contract: str, iteration_phase: str, context: Dict[str, Any]) -> WorkflowPlan:
        """
        Create an optimized workflow plan for the given context.
        
        Args:
            target_contract: Target contract address
            iteration_phase: Current iteration phase
            context: Analysis context and constraints
            
        Returns:
            Optimized workflow plan
        """
        plan_id = f"workflow_{int(time.time())}_{iteration_phase}"
        
        base_template = self.workflow_templates.get(iteration_phase, [])
        
        adapted_executions = await self._adapt_workflow_template(base_template, context)
        
        optimized_executions = self._optimize_execution_order(adapted_executions)
        
        total_cost = sum(exec.estimated_cost for exec in optimized_executions)
        total_duration = self._estimate_workflow_duration(optimized_executions)
        
        parallel_groups = self._generate_parallel_groups(optimized_executions)
        
        dependency_graph = self._build_dependency_graph(optimized_executions)
        
        return WorkflowPlan(
            plan_id=plan_id,
            target_contract=target_contract,
            iteration_phase=iteration_phase,
            tool_executions=optimized_executions,
            estimated_total_cost=total_cost,
            estimated_duration=total_duration,
            parallel_groups=parallel_groups,
            dependency_graph=dependency_graph
        )
    
    async def _adapt_workflow_template(self, template: List[Dict[str, Any]], context: Dict[str, Any]) -> List[ToolExecution]:
        """
        Adapt workflow template based on analysis context.
        
        Args:
            template: Base workflow template
            context: Analysis context and constraints
            
        Returns:
            List of adapted tool executions
        """
        adapted_executions = []
        
        for step in template:
            tool_name = step['tool']
            method_name = step['method']
            
            tool_meta = self.tool_metadata.get(tool_name, {})
            
            priority = self._determine_execution_priority(tool_name, step, context)
            
            if priority == ToolPriority.OPTIONAL and context.get('budget_constrained', False):
                continue
            
            execution_mode = self._determine_execution_mode(tool_name, step, context)
            
            parameters = await self._build_tool_parameters(tool_name, method_name, context)
            
            execution = ToolExecution(
                tool_name=tool_name,
                method_name=method_name,
                parameters=parameters,
                priority=priority,
                execution_mode=execution_mode,
                dependencies=step.get('depends_on', []),
                timeout=tool_meta.get('avg_execution_time', 10) * 3,  # 3x avg time as timeout
                retry_count=self.max_retries,
                estimated_cost=tool_meta.get('estimated_cost', 50),
                expected_output_type=tool_meta.get('output_types', ['unknown'])[0]
            )
            
            adapted_executions.append(execution)
        
        return adapted_executions
    
    def _determine_execution_priority(self, tool_name: str, step: Dict[str, Any], context: Dict[str, Any]) -> ToolPriority:
        """Determine execution priority based on context."""
        tool_meta = self.tool_metadata.get(tool_name, {})
        phase = context.get('iteration_phase', 'analysis')
        
        base_priority = tool_meta.get('priority_by_phase', {}).get(phase, ToolPriority.MEDIUM)
        
        if context.get('high_value_target', False):
            if base_priority == ToolPriority.MEDIUM:
                base_priority = ToolPriority.HIGH
            elif base_priority == ToolPriority.LOW:
                base_priority = ToolPriority.MEDIUM
        
        success_rate = self.tool_success_rates.get(tool_name, 1.0)
        if success_rate < 0.5:  # Low success rate
            if base_priority == ToolPriority.CRITICAL:
                base_priority = ToolPriority.HIGH
            elif base_priority == ToolPriority.HIGH:
                base_priority = ToolPriority.MEDIUM
        
        return base_priority
    
    def _determine_execution_mode(self, tool_name: str, step: Dict[str, Any], context: Dict[str, Any]) -> ExecutionMode:
        """Determine execution mode based on tool characteristics and context."""
        tool_meta = self.tool_metadata.get(tool_name, {})
        
        if not tool_meta.get('parallel_safe', True):
            return ExecutionMode.SEQUENTIAL
        
        if step.get('depends_on'):
            return ExecutionMode.CONDITIONAL
        
        return ExecutionMode.PARALLEL
    
    async def _build_tool_parameters(self, tool_name: str, method_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build parameters for tool execution based on context.
        
        Args:
            tool_name: Name of the tool
            method_name: Method to execute
            context: Analysis context
            
        Returns:
            Parameters dictionary for tool execution
        """
        base_params = {
            'target_contract': context.get('target_contract'),
            'chain': context.get('chain', 'ethereum')
        }
        
        if tool_name == 'source_code_fetcher':
            base_params.update({
                'contract_address': context.get('target_contract'),
                'chain': context.get('chain', 'ethereum')
            })
        
        elif tool_name == 'constructor_parameter':
            base_params.update({
                'contract_address': context.get('target_contract')
            })
        
        elif tool_name == 'state_reader':
            base_params.update({
                'contract_address': context.get('target_contract'),
                'abi': context.get('contract_abi', []),
                'block_number': context.get('block_number')
            })
        
        elif tool_name == 'code_sanitizer':
            base_params.update({
                'source_code': context.get('source_code', '')
            })
        
        elif tool_name == 'concrete_execution':
            if method_name == 'create_blockchain_fork':
                base_params.update({
                    'chain': context.get('chain', 'ethereum'),
                    'block_number': context.get('fork_block_number')
                })
            elif method_name == 'setup_forge_project':
                base_params.update({
                    'project_name': f"exploit_{context.get('target_contract', 'unknown')[:8]}",
                    'fork_id': context.get('fork_id')
                })
        
        elif tool_name == 'revenue_normalizer':
            base_params.update({
                'address': context.get('target_contract'),
                'token_addresses': context.get('token_addresses', []),
                'chain_id': 1 if context.get('chain') == 'ethereum' else 56
            })
        
        return base_params
    
    def _optimize_execution_order(self, executions: List[ToolExecution]) -> List[ToolExecution]:
        """
        Optimize execution order based on dependencies and priorities.
        
        Args:
            executions: List of tool executions to optimize
            
        Returns:
            Optimized execution order
        """
        priority_order = {
            ToolPriority.CRITICAL: 0,
            ToolPriority.HIGH: 1,
            ToolPriority.MEDIUM: 2,
            ToolPriority.LOW: 3,
            ToolPriority.OPTIONAL: 4
        }
        
        sorted_executions = []
        remaining_executions = executions.copy()
        
        while remaining_executions:
            ready_executions = []
            
            for execution in remaining_executions:
                dependencies_met = all(
                    any(completed.tool_name == dep for completed in sorted_executions)
                    for dep in execution.dependencies
                )
                
                if dependencies_met:
                    ready_executions.append(execution)
            
            if not ready_executions:
                ready_executions = sorted(
                    remaining_executions,
                    key=lambda x: priority_order.get(x.priority, 5)
                )[:1]
            
            ready_executions.sort(
                key=lambda x: (
                    priority_order.get(x.priority, 5),
                    x.estimated_cost / max(self.tool_cost_effectiveness.get(x.tool_name, 1.0), 0.1)
                )
            )
            
            next_execution = ready_executions[0]
            sorted_executions.append(next_execution)
            remaining_executions.remove(next_execution)
        
        return sorted_executions
    
    def _estimate_workflow_duration(self, executions: List[ToolExecution]) -> float:
        """
        Estimate total workflow duration considering parallelization.
        
        Args:
            executions: List of tool executions
            
        Returns:
            Estimated duration in seconds
        """
        execution_timeline = {}
        
        for execution in executions:
            start_time = 0.0
            
            for dep in execution.dependencies:
                dep_execution = next((e for e in executions if e.tool_name == dep), None)
                if dep_execution and dep in execution_timeline:
                    dep_end_time = execution_timeline[dep]['end_time']
                    start_time = max(start_time, dep_end_time)
            
            tool_meta = self.tool_metadata.get(execution.tool_name, {})
            exec_time = self.tool_avg_execution_times.get(
                execution.tool_name,
                tool_meta.get('avg_execution_time', 10.0)
            )
            
            execution_timeline[execution.tool_name] = {
                'start_time': start_time,
                'end_time': start_time + exec_time,
                'duration': exec_time
            }
        
        return max(timeline['end_time'] for timeline in execution_timeline.values()) if execution_timeline else 0.0
    
    def _generate_parallel_groups(self, executions: List[ToolExecution]) -> List[List[str]]:
        """
        Generate parallel execution groups based on dependencies and constraints.
        
        Args:
            executions: List of tool executions
            
        Returns:
            List of parallel execution groups
        """
        parallel_groups = []
        remaining_tools = [e.tool_name for e in executions]
        
        while remaining_tools:
            current_group = []
            
            for tool_name in remaining_tools.copy():
                execution = next(e for e in executions if e.tool_name == tool_name)
                
                dependencies_met = all(
                    dep not in remaining_tools for dep in execution.dependencies
                )
                
                can_parallel = (
                    execution.execution_mode in [ExecutionMode.PARALLEL, ExecutionMode.ADAPTIVE] and
                    self.tool_metadata.get(tool_name, {}).get('parallel_safe', True)
                )
                
                if dependencies_met and (can_parallel or not current_group):
                    current_group.append(tool_name)
                    remaining_tools.remove(tool_name)
                    
                    if len(current_group) >= self.max_parallel_executions:
                        break
            
            if current_group:
                parallel_groups.append(current_group)
            else:
                parallel_groups.extend([[tool] for tool in remaining_tools])
                break
        
        return parallel_groups
    
    def _build_dependency_graph(self, executions: List[ToolExecution]) -> Dict[str, List[str]]:
        """
        Build dependency graph for execution planning.
        
        Args:
            executions: List of tool executions
            
        Returns:
            Dependency graph mapping tool names to their dependencies
        """
        return {
            execution.tool_name: execution.dependencies
            for execution in executions
        }
    
    async def execute_workflow(self, workflow_plan: WorkflowPlan, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete workflow plan.
        
        Args:
            workflow_plan: Workflow plan to execute
            context: Execution context and parameters
            
        Returns:
            Workflow execution results
        """
        record_heartbeat()
        logger.info(f"Executing workflow {workflow_plan.plan_id} with {len(workflow_plan.tool_executions)} tools")
        
        start_time = time.time()
        execution_results = {}
        failed_executions = []
        
        for group_idx, parallel_group in enumerate(workflow_plan.parallel_groups):
            set_queue_depth(len(workflow_plan.parallel_groups) - group_idx)
            logger.info(f"Executing parallel group {group_idx + 1}/{len(workflow_plan.parallel_groups)}: {parallel_group}")
            
            group_results = await self._execute_parallel_group(parallel_group, workflow_plan, context)
            
            execution_results.update(group_results)
            
            context.update(self._extract_context_updates(group_results))
            
            group_failures = [tool for tool, result in group_results.items() if not result.success]
            if group_failures:
                failed_executions.extend(group_failures)
                
                critical_failures = [
                    tool for tool in group_failures
                    if any(e.tool_name == tool and e.priority == ToolPriority.CRITICAL 
                          for e in workflow_plan.tool_executions)
                ]
                
                if critical_failures:
                    logger.error(f"Critical tools failed: {critical_failures}")
                    break
        
        total_execution_time = time.time() - start_time
        
        self._update_performance_metrics(execution_results)
        
        workflow_summary = {
            'workflow_id': workflow_plan.plan_id,
            'target_contract': workflow_plan.target_contract,
            'iteration_phase': workflow_plan.iteration_phase,
            'total_execution_time': total_execution_time,
            'successful_tools': len([r for r in execution_results.values() if r.success]),
            'failed_tools': len(failed_executions),
            'total_resource_usage': sum(r.resource_usage.get('cost', 0) for r in execution_results.values()),
            'execution_results': execution_results,
            'failed_executions': failed_executions
        }
        
        logger.info(f"Workflow {workflow_plan.plan_id} completed in {total_execution_time:.2f}s")
        
        return workflow_summary
    
    async def _execute_parallel_group(self, parallel_group: List[str], workflow_plan: WorkflowPlan, context: Dict[str, Any]) -> Dict[str, ExecutionResult]:
        """
        Execute a group of tools in parallel.
        
        Args:
            parallel_group: List of tool names to execute in parallel
            workflow_plan: Complete workflow plan
            context: Execution context
            
        Returns:
            Dictionary mapping tool names to execution results
        """
        set_queue_depth(len(parallel_group))
        tasks = []
        
        for tool_name in parallel_group:
            execution = next(e for e in workflow_plan.tool_executions if e.tool_name == tool_name)
            task = asyncio.create_task(
                self._execute_single_tool(execution, context),
                name=f"execute_{tool_name}"
            )
            tasks.append((tool_name, task))
        
        results = {}
        
        try:
            completed_tasks = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )
            
            for (tool_name, _), result in zip(tasks, completed_tasks):
                if isinstance(result, Exception):
                    logger.error(f"Tool {tool_name} failed with exception: {result}")
                    results[tool_name] = ExecutionResult(
                        tool_name=tool_name,
                        method_name="unknown",
                        success=False,
                        result=None,
                        execution_time=0.0,
                        resource_usage={},
                        error_message=str(result)
                    )
                else:
                    results[tool_name] = result
        
        except Exception as e:
            logger.error(f"Parallel group execution failed: {e}")
            
            for tool_name in parallel_group:
                results[tool_name] = ExecutionResult(
                    tool_name=tool_name,
                    method_name="unknown",
                    success=False,
                    result=None,
                    execution_time=0.0,
                    resource_usage={},
                    error_message=f"Group execution failed: {e}"
                )
        
        return results
    
    async def _execute_single_tool(self, execution: ToolExecution, context: Dict[str, Any]) -> ExecutionResult:
        """Execute a single tool with retry, restart and error tracking."""

        for restart_attempt in range(self.watchdog_restart_limit + 1):
            start_time = time.time()
            last_error = None

            for attempt in range(execution.retry_count + 1):
                try:
                    logger.debug(
                        f"Executing {execution.tool_name}.{execution.method_name} "
                        f"(attempt {attempt + 1}, restart {restart_attempt})"
                    )

                    tool = self.tools.get(execution.tool_name)
                    if not tool:
                        raise ValueError(f"Tool {execution.tool_name} not available")

                    method = getattr(tool, execution.method_name, None)
                    if not method:
                        raise ValueError(f"Method {execution.method_name} not found on {execution.tool_name}")

                    result = await asyncio.wait_for(
                        method(**execution.parameters),
                        timeout=execution.timeout,
                    )

                    execution_time = time.time() - start_time

                    resource_usage = {
                        'cost': execution.estimated_cost,
                        'execution_time': execution_time,
                        'memory_usage': 0,  # Would be measured in real implementation
                        'api_calls': 1,
                    }

                    return ExecutionResult(
                        tool_name=execution.tool_name,
                        method_name=execution.method_name,
                        success=True,
                        result=result,
                        execution_time=execution_time,
                        resource_usage=resource_usage,
                        retry_attempts=attempt,
                    )

                except asyncio.TimeoutError:
                    last_error = f"Execution timeout after {execution.timeout}s"
                    record_error()
                    logger.warning(
                        f"{execution.tool_name}.{execution.method_name} timed out "
                        f"(attempt {attempt + 1}, restart {restart_attempt})"
                    )

                except Exception as e:
                    last_error = str(e)
                    record_error()
                    logger.warning(
                        f"{execution.tool_name}.{execution.method_name} failed: {e} "
                        f"(attempt {attempt + 1}, restart {restart_attempt})"
                    )

                if attempt < execution.retry_count:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff

            # After retry attempts exhausted
            self.tool_failure_counts[execution.tool_name] += 1
            if self.tool_failure_counts[execution.tool_name] >= self.watchdog_escalate_threshold:
                self._escalate_failure(execution.tool_name, last_error)
                break

            if restart_attempt < self.watchdog_restart_limit:
                logger.info(
                    f"Watchdog restarting {execution.tool_name} after failure"
                )
                self._restart_tool(execution.tool_name)
                continue

            break

        execution_time = time.time() - start_time
        return ExecutionResult(
            tool_name=execution.tool_name,
            method_name=execution.method_name,
            success=False,
            result=None,
            execution_time=execution_time,
            resource_usage={'cost': 0},
            error_message=last_error,
            retry_attempts=execution.retry_count,
        )
    
    def _extract_context_updates(self, group_results: Dict[str, ExecutionResult]) -> Dict[str, Any]:
        """
        Extract context updates from group execution results.
        
        Args:
            group_results: Results from parallel group execution
            
        Returns:
            Context updates for subsequent groups
        """
        context_updates = {}
        
        for tool_name, result in group_results.items():
            if result.success and result.result:
                if tool_name == 'source_code_fetcher':
                    if hasattr(result.result, 'source_code'):
                        context_updates['source_code'] = result.result.source_code
                    if hasattr(result.result, 'abi'):
                        context_updates['contract_abi'] = result.result.abi
                
                elif tool_name == 'constructor_parameter':
                    if hasattr(result.result, 'parameters'):
                        context_updates['constructor_params'] = result.result.parameters
                
                elif tool_name == 'state_reader':
                    if hasattr(result.result, 'state_data'):
                        context_updates['state_snapshot'] = result.result.state_data
                
                elif tool_name == 'concrete_execution':
                    if result.method_name == 'create_blockchain_fork':
                        context_updates['fork_id'] = result.result
                    elif result.method_name == 'setup_forge_project':
                        context_updates['project_path'] = result.result

        return context_updates

    def _restart_tool(self, tool_name: str) -> None:
        """Attempt to restart a tool after a failure."""

        tool = self.tools.get(tool_name)
        if not tool:
            return
        try:
            if hasattr(tool, 'restart'):
                tool.restart()
            else:
                tool_cls = tool.__class__
                config = getattr(tool, 'config', {})
                self.tools[tool_name] = tool_cls(**config) if config else tool_cls()
            logger.info(f"Tool {tool_name} restarted by watchdog")
        except Exception as e:
            logger.error(f"Failed to restart tool {tool_name}: {e}")

    def _escalate_failure(self, tool_name: str, error: Optional[str]) -> None:
        """Escalate repeated tool failures for external handling."""

        logger.critical(
            f"Tool {tool_name} failed repeatedly: {error}. Escalating to supervisor"
        )
    
    def _update_performance_metrics(self, execution_results: Dict[str, ExecutionResult]):
        """
        Update performance metrics based on execution results.
        
        Args:
            execution_results: Results from workflow execution
        """
        for tool_name, result in execution_results.items():
            if tool_name not in self.tool_success_rates:
                self.tool_success_rates[tool_name] = 1.0 if result.success else 0.0
            else:
                alpha = 0.3
                self.tool_success_rates[tool_name] = (
                    alpha * (1.0 if result.success else 0.0) +
                    (1 - alpha) * self.tool_success_rates[tool_name]
                )
            
            if tool_name not in self.tool_avg_execution_times:
                self.tool_avg_execution_times[tool_name] = result.execution_time
            else:
                alpha = 0.3
                self.tool_avg_execution_times[tool_name] = (
                    alpha * result.execution_time +
                    (1 - alpha) * self.tool_avg_execution_times[tool_name]
                )
            
            cost = result.resource_usage.get('cost', 1)
            effectiveness = (1.0 if result.success else 0.0) / max(cost, 1)
            
            if tool_name not in self.tool_cost_effectiveness:
                self.tool_cost_effectiveness[tool_name] = effectiveness
            else:
                alpha = 0.3
                self.tool_cost_effectiveness[tool_name] = (
                    alpha * effectiveness +
                    (1 - alpha) * self.tool_cost_effectiveness[tool_name]
                )
        
        self.execution_history.extend(execution_results.values())
        
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary for all tools.
        
        Returns:
            Performance summary with metrics and recommendations
        """
        summary = {
            'total_executions': len(self.execution_history),
            'tool_performance': {},
            'overall_metrics': {
                'average_success_rate': 0.0,
                'average_execution_time': 0.0,
                'total_resource_usage': 0
            },
            'recommendations': []
        }
        
        if not self.execution_history:
            return summary
        
        successful_executions = [r for r in self.execution_history if r.success]
        summary['overall_metrics']['average_success_rate'] = len(successful_executions) / len(self.execution_history)
        summary['overall_metrics']['average_execution_time'] = sum(r.execution_time for r in self.execution_history) / len(self.execution_history)
        summary['overall_metrics']['total_resource_usage'] = sum(r.resource_usage.get('cost', 0) for r in self.execution_history)
        
        for tool_name in self.tool_metadata.keys():
            tool_executions = [r for r in self.execution_history if r.tool_name == tool_name]
            
            if tool_executions:
                successful_tool_executions = [r for r in tool_executions if r.success]
                summary['tool_performance'][tool_name] = {
                    'success_rate': len(successful_tool_executions) / len(tool_executions),
                    'average_execution_time': sum(r.execution_time for r in tool_executions) / len(tool_executions),
                    'total_executions': len(tool_executions),
                    'cost_effectiveness': self.tool_cost_effectiveness.get(tool_name, 0.0)
                }
        
        return summary
