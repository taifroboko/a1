"""
Main Execution Pipeline - A1 Agentic System

Central orchestration system that coordinates all components for autonomous
smart contract exploit generation and analysis.

Based on the A1 research paper specifications.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import sys
import os
from datetime import datetime

from core.agent import A1Agent
from core.orchestrator import ToolOrchestrator
from core.feedback import FeedbackProcessor
from core.strategy import StrategyGenerator
from core.queue import ContractQueue, QueueItem

from tools.source_code_fetcher import SourceCodeFetcher
from tools.constructor_parameter import ConstructorParameterTool
from tools.state_reader import BlockchainStateReader
from tools.code_sanitizer import CodeSanitizer
from tools.concrete_execution import ConcreteExecutionTool
from tools.revenue_normalizer import RevenueNormalizer

from blockchain.client import BlockchainClient
from blockchain.scanner import BlockchainScanner
from blockchain.forge import ForgeIntegration

from utils.dex_utils import DexRouter, TokenUtils

from storage.result_storage import ResultStorage, StoredResult
from config.configuration_manager import ConfigurationManager
from monitoring.logger import SystemLogger
from monitoring.metrics_collector import MetricsCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('a1_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

@dataclass
class ContractTarget:
    """Contract target for analysis"""
    address: str
    network: str
    name: Optional[str] = None
    description: Optional[str] = None
    priority: int = 1
    tags: List[str] = None

@dataclass
class ExecutionResult:
    """Result of contract analysis execution"""
    contract_address: str
    network: str
    success: bool
    execution_time: float
    iterations_used: int
    strategies_generated: int
    exploits_found: int
    total_profit_potential: float
    confidence_score: float
    error_message: Optional[str] = None
    detailed_results: Dict[str, Any] = None
    source_hash: Optional[str] = None
    state_hash: Optional[str] = None
    cached: bool = False

class ContractProcessor:
    """
    Main contract processor that orchestrates the entire A1 system workflow.
    
    Coordinates all tools, agents, and analysis components to perform
    autonomous exploit generation for smart contracts.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the contract processor.
        
        Args:
            config: System configuration dictionary
        """
        self.config = config
        self.config_manager = ConfigurationManager()
        
        self.agent: Optional[A1Agent] = None
        self.orchestrator: Optional[ToolOrchestrator] = None
        self.feedback_processor: Optional[FeedbackProcessor] = None
        self.strategy_generator: Optional[StrategyGenerator] = None
        
        self.tools: Dict[str, Any] = {}
        
        self.blockchain_client: Optional[BlockchainClient] = None
        self.scanner: Optional[BlockchainScanner] = None
        self.forge: Optional[ForgeIntegration] = None
        
        self.dex_router: Optional[DexRouter] = None
        self.token_utils: Optional[TokenUtils] = None
        
        self.result_storage: Optional[ResultStorage] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.system_logger: Optional[SystemLogger] = None
        
        self.is_initialized = False
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        self.total_contracts_processed = 0
        self.successful_analyses = 0
        self.total_exploits_found = 0
        self.total_execution_time = 0.0
    
    async def initialize(self):
        """Initialize all system components."""
        try:
            logger.info("Initializing A1 Agentic System...")
            
            self.system_logger = SystemLogger(self.config)
            self.metrics_collector = MetricsCollector(self.config)
            
            self.result_storage = ResultStorage(self.config)
            await self.result_storage.initialize()
            
            self.blockchain_client = BlockchainClient(self.config)
            await self.blockchain_client.__aenter__()
            
            self.scanner = BlockchainScanner(self.config)
            await self.scanner.__aenter__()
            
            self.forge = ForgeIntegration(self.config)
            await self.forge.initialize()
            
            self.dex_router = DexRouter(self.config)
            await self.dex_router.__aenter__()
            
            self.token_utils = TokenUtils(self.config)
            await self.token_utils.__aenter__()
            
            await self._initialize_tools()
            
            self.feedback_processor = FeedbackProcessor(self.config)
            self.strategy_generator = StrategyGenerator(self.config)
            self.orchestrator = ToolOrchestrator(self.tools, self.config)

            self.agent = A1Agent(
                self.config,
                blockchain_client=self.blockchain_client,
                forge=self.forge,
                result_storage=self.result_storage,
            )
            
            self.is_initialized = True
            logger.info("A1 Agentic System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize A1 system: {e}")
            raise
    
    async def _initialize_tools(self):
        """Initialize all domain-specific tools."""
        tool_configs = {
            'source_code_fetcher': SourceCodeFetcher,
            'constructor_parameter': ConstructorParameterTool,
            'state_reader': BlockchainStateReader,
            'code_sanitizer': CodeSanitizer,
            'concrete_execution': ConcreteExecutionTool,
            'revenue_normalizer': RevenueNormalizer
        }
        
        for tool_name, tool_class in tool_configs.items():
            try:
                api_config = self.config_manager.get_api_config()
                
                if tool_name == 'source_code_fetcher':
                    tool_instance = tool_class(
                        web3_client=self.blockchain_client.get_web3('ethereum'),
                        etherscan_api_key=api_config.etherscan_api_key,
                        bscscan_api_key=api_config.bscscan_api_key
                    )
                elif tool_name == 'constructor_parameter':
                    tool_instance = tool_class(
                        web3_client=self.blockchain_client.get_web3('ethereum'),
                        etherscan_api_key=api_config.etherscan_api_key,
                        bscscan_api_key=api_config.bscscan_api_key
                    )
                elif tool_name == 'state_reader':
                    tool_instance = tool_class(
                        web3_client=self.blockchain_client.get_web3('ethereum')
                    )
                elif tool_name == 'code_sanitizer':
                    tool_instance = tool_class()
                elif tool_name == 'concrete_execution':
                    api_config = self.config_manager.get_api_config()
                    tool_instance = tool_class(
                        ethereum_rpc_url=api_config.alchemy_eth_url,
                        bsc_rpc_url=api_config.alchemy_bnb_url
                    )
                elif tool_name == 'revenue_normalizer':
                    tool_instance = tool_class(self.config)
                else:
                    tool_instance = tool_class(self.config)
                
                if hasattr(tool_instance, 'initialize'):
                    await tool_instance.initialize()
                self.tools[tool_name] = tool_instance
                logger.info(f"Initialized tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to initialize tool {tool_name}: {e}")
                raise
    
    async def process_contract(self, contract_target: ContractTarget, force: bool = False) -> ExecutionResult:
        """
        Process a single contract for exploit analysis.
        
        Args:
            contract_target: Contract to analyze
            
        Returns:
            Execution result with analysis outcomes
        """
        if not self.is_initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        start_time = time.time()
        session_id = f"{contract_target.address}_{int(start_time)}"
        
        logger.info(f"Starting analysis for contract {contract_target.address} on {contract_target.network}")
        
        try:
            session = await self._create_execution_session(session_id, contract_target)
            self.active_sessions[session_id] = session

            result = await self._execute_analysis_workflow(session_id, contract_target, force)

            if not result.cached:
                await self._store_execution_result(session_id, result)

            self._update_performance_metrics(result)
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            logger.info(f"Completed analysis for {contract_target.address} in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process contract {contract_target.address}: {e}")
            
            execution_time = time.time() - start_time
            return ExecutionResult(
                contract_address=contract_target.address,
                network=contract_target.network,
                success=False,
                execution_time=execution_time,
                iterations_used=0,
                strategies_generated=0,
                exploits_found=0,
                total_profit_potential=0.0,
                confidence_score=0.0,
                error_message=str(e)
            )
        
        finally:
            if session_id in self.active_sessions:
                await self._cleanup_session(session_id)
                del self.active_sessions[session_id]
    
    async def _create_execution_session(self, session_id: str, contract_target: ContractTarget) -> Dict[str, Any]:
        """Create a new execution session."""
        session = {
            "id": session_id,
            "contract_target": contract_target,
            "start_time": time.time(),
            "status": "initializing",
            "context": {},
            "tool_results": {},
            "strategies": [],
            "exploits": [],
            "feedback_history": [],
            "metrics": {
                "iterations": 0,
                "tool_executions": 0,
                "api_calls": 0,
                "gas_estimates": 0
            }
        }
        
        session["context"] = await self._build_contract_context(contract_target)
        session["status"] = "ready"
        
        return session
    
    async def _build_contract_context(self, contract_target: ContractTarget) -> Dict[str, Any]:
        """Build comprehensive context for contract analysis."""
        context = {
            "contract_address": contract_target.address,
            "network": contract_target.network,
            "metadata": {},
            "source_code": None,
            "abi": None,
            "bytecode": None,
            "creation_info": {},
            "transaction_history": [],
            "token_info": None,
            "dex_interactions": [],
            "security_flags": []
        }
        
        try:
            scanner_type = self.scanner.get_scanner_for_network(contract_target.network)
            if scanner_type:
                source_info = await self.scanner.get_contract_source_code(
                    scanner_type, contract_target.address
                )
                if source_info:
                    context["source_code"] = source_info.source_code
                    context["abi"] = source_info.abi
                    context["metadata"] = {
                        "contract_name": source_info.contract_name,
                        "compiler_version": source_info.compiler_version,
                        "optimization_enabled": source_info.optimization_enabled,
                        "verification_status": source_info.verification_status.value
                    }
            
            if scanner_type:
                creation_info = await self.scanner.get_contract_creation_info(
                    scanner_type, contract_target.address
                )
                if creation_info:
                    context["creation_info"] = creation_info
            
            if scanner_type:
                transactions = await self.scanner.get_contract_transactions(
                    scanner_type, contract_target.address, offset=50
                )
                context["transaction_history"] = transactions[:20]  # Keep recent 20
            
            if scanner_type:
                token_info = await self.scanner.get_token_info(
                    scanner_type, contract_target.address
                )
                if token_info:
                    context["token_info"] = asdict(token_info)
            
            try:
                bytecode = await self.blockchain_client.get_code(contract_target.address)
                balance = await self.blockchain_client.get_balance(contract_target.address)
                context["bytecode"] = bytecode
                context["balance"] = balance
            except Exception as e:
                logger.debug(f"Could not fetch contract info: {e}")
            
        except Exception as e:
            logger.warning(f"Failed to build complete context for {contract_target.address}: {e}")
        
        return context
    
    async def _execute_analysis_workflow(self, session_id: str, contract_target: ContractTarget, force: bool = False) -> ExecutionResult:
        """Execute the main A1 analysis workflow."""
        session = self.active_sessions[session_id]

        try:
            logger.info(f"Phase 1: Initial analysis for {contract_target.address}")
            initial_analysis = await self.agent.execute_full_analysis(
                contract_target.address, contract_target.network, force=force
            )

            if isinstance(initial_analysis, StoredResult):
                return ExecutionResult(
                    contract_address=initial_analysis.contract_address,
                    network=initial_analysis.network,
                    success=initial_analysis.success,
                    execution_time=0.0,
                    iterations_used=initial_analysis.iterations_used,
                    strategies_generated=initial_analysis.strategies_generated,
                    exploits_found=initial_analysis.exploits_found,
                    total_profit_potential=initial_analysis.total_profit_potential,
                    confidence_score=initial_analysis.confidence_score,
                    detailed_results=initial_analysis.detailed_results or {},
                    source_hash=initial_analysis.source_hash,
                    state_hash=initial_analysis.state_hash,
                    cached=True,
                )

            if not initial_analysis.get("success", False):
                return ExecutionResult(
                    contract_address=contract_target.address,
                    network=contract_target.network,
                    success=False,
                    execution_time=0.0,
                    iterations_used=0,
                    strategies_generated=0,
                    exploits_found=0,
                    total_profit_potential=0.0,
                    confidence_score=0.0,
                    error_message="Contract analysis failed",
                )

            strategies_generated = len(initial_analysis.get("strategies", []))
            exploits_found = len(initial_analysis.get("exploits", []))
            total_profit_potential = initial_analysis.get("total_profit_potential", 0.0)
            best_confidence = initial_analysis.get("confidence_score", 0.0)
            iterations_used = initial_analysis.get("iterations_used", 1)

            logger.info(f"Phase 3: Final analysis for {contract_target.address}")

            final_analysis = await self._perform_final_analysis(session)

            return ExecutionResult(
                contract_address=contract_target.address,
                network=contract_target.network,
                success=exploits_found > 0,
                execution_time=0.0,  # Will be set by caller
                iterations_used=session["metrics"]["iterations"],
                strategies_generated=strategies_generated,
                exploits_found=exploits_found,
                total_profit_potential=total_profit_potential,
                confidence_score=best_confidence,
                detailed_results=final_analysis,
                source_hash=self.agent.current_source_hash,
                state_hash=self.agent.current_state_hash,
            )

        except Exception as e:
            logger.error(f"Analysis workflow failed for {contract_target.address}: {e}")
            raise

    async def _perform_final_analysis(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Perform final analysis and generate comprehensive report."""
        try:
            final_analysis = {
                "session_summary": {
                    "total_strategies": len(session["strategies"]),
                    "successful_exploits": len(session["exploits"]),
                    "iterations_completed": session["metrics"]["iterations"],
                    "total_profit_potential": sum(
                        exploit["profit_potential"] for exploit in session["exploits"]
                    )
                },
                "best_exploits": sorted(
                    session["exploits"], 
                    key=lambda x: x["confidence_score"], 
                    reverse=True
                )[:5],  # Top 5 exploits
                "vulnerability_analysis": await self._analyze_vulnerabilities(session),
                "economic_impact": await self._calculate_economic_impact(session),
                "risk_assessment": await self._assess_risks(session),
                "recommendations": await self._generate_recommendations(session),
                "technical_details": {
                    "tool_executions": session["metrics"]["tool_executions"],
                    "api_calls": session["metrics"]["api_calls"],
                    "gas_estimates": session["metrics"]["gas_estimates"]
                }
            }
            
            return final_analysis
            
        except Exception as e:
            logger.error(f"Failed to perform final analysis: {e}")
            return {"error": str(e)}
    
    async def _analyze_vulnerabilities(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze vulnerabilities found in the contract."""
        vulnerabilities = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "informational": []
        }
        
        for exploit in session["exploits"]:
            strategy = exploit["strategy"]
            vulnerability_type = strategy.get("vulnerability_type", "unknown")
            severity = strategy.get("severity", "medium")
            
            if severity in vulnerabilities:
                vulnerabilities[severity].append({
                    "type": vulnerability_type,
                    "description": strategy.get("description", ""),
                    "profit_potential": exploit["profit_potential"],
                    "confidence": exploit["confidence_score"]
                })
        
        return vulnerabilities
    
    async def _calculate_economic_impact(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate economic impact of found exploits."""
        total_profit = sum(exploit["profit_potential"] for exploit in session["exploits"])
        
        contract_address = session["contract_target"].address
        tvl_estimate = 0.0
        
        try:
            if session["context"].get("token_info"):
                pass
        except Exception:
            pass
        
        return {
            "total_profit_potential": total_profit,
            "estimated_tvl": tvl_estimate,
            "impact_percentage": (total_profit / max(tvl_estimate, 1)) * 100,
            "exploit_categories": {
                "flash_loan": sum(
                    e["profit_potential"] for e in session["exploits"] 
                    if "flash_loan" in e["strategy"].get("execution_type", "")
                ),
                "arbitrage": sum(
                    e["profit_potential"] for e in session["exploits"] 
                    if "arbitrage" in e["strategy"].get("execution_type", "")
                ),
                "manipulation": sum(
                    e["profit_potential"] for e in session["exploits"] 
                    if "manipulation" in e["strategy"].get("execution_type", "")
                )
            }
        }
    
    async def _assess_risks(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risks associated with found exploits."""
        return {
            "execution_risk": "medium",  # Risk of exploit execution failing
            "detection_risk": "low",     # Risk of exploit being detected
            "legal_risk": "high",        # Legal implications
            "technical_risk": "medium",  # Technical complexity
            "market_risk": "medium",     # Market conditions affecting profitability
            "overall_risk": "medium"
        }
    
    async def _generate_recommendations(self, session: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if session["exploits"]:
            recommendations.append("Critical vulnerabilities found - immediate remediation required")
            recommendations.append("Implement additional security measures and access controls")
            recommendations.append("Consider bug bounty program for ongoing security assessment")
        
        if len(session["strategies"]) > len(session["exploits"]):
            recommendations.append("Some attack vectors were identified but not exploitable")
            recommendations.append("Monitor for changes that could make these vectors viable")
        
        recommendations.extend([
            "Regular security audits recommended",
            "Implement monitoring for unusual transaction patterns",
            "Consider upgrading to more secure contract patterns"
        ])
        
        return recommendations
    
    async def _store_execution_result(self, session_id: str, result: ExecutionResult):
        """Store execution result in persistent storage."""
        try:
            await self.result_storage.store_result(session_id, result)
            logger.info(f"Stored execution result for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to store execution result: {e}")
    
    def _update_performance_metrics(self, result: ExecutionResult):
        """Update system performance metrics."""
        self.total_contracts_processed += 1
        if result.success:
            self.successful_analyses += 1
        self.total_exploits_found += result.exploits_found
        self.total_execution_time += result.execution_time
        
        if self.metrics_collector:
            self.metrics_collector.record_execution(result)
    
    async def _cleanup_session(self, session_id: str):
        """Clean up resources for a completed session."""
        try:
            if self.forge:
                await self.forge.cleanup()
            
            logger.debug(f"Cleaned up session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup session {session_id}: {e}")
    
    async def process_batch(self, contract_targets: List[ContractTarget], max_concurrent: int = 3, force: bool = False) -> List[ExecutionResult]:
        """
        Process multiple contracts concurrently.
        
        Args:
            contract_targets: List of contracts to analyze
            max_concurrent: Maximum concurrent executions
            
        Returns:
            List of execution results
        """
        if not self.is_initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        logger.info(f"Starting batch processing of {len(contract_targets)} contracts")
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(target):
            async with semaphore:
                return await self.process_contract(target, force=force)
        
        tasks = [process_with_semaphore(target) for target in contract_targets]
        
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            logger.info(f"Batch progress: {completed}/{len(contract_targets)} completed")
            
            if result.success:
                logger.info(f"✓ {result.contract_address}: {result.exploits_found} exploits, ${result.total_profit_potential:.2f} profit")
            else:
                logger.warning(f"✗ {result.contract_address}: {result.error_message}")
        
        logger.info(f"Batch processing completed: {len(results)} results")
        return results

    async def process_queue(self, queue: ContractQueue, max_concurrent: int = 3, force: bool = False) -> None:
        """Continuously process contracts from a message queue.

        Args:
            queue: :class:`ContractQueue` instance to pull jobs from.
            max_concurrent: Maximum number of concurrent analyses.
        """

        if not self.is_initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")

        semaphore = asyncio.Semaphore(max_concurrent)
        active: set[asyncio.Task] = set()

        async def handle(item: QueueItem):
            async with semaphore:
                target = ContractTarget(address=item.address, network=item.network)
                await self.process_contract(target, force=force)

        try:
            async for item in queue.consume():
                task = asyncio.create_task(handle(item))
                active.add(task)
                task.add_done_callback(lambda t: active.discard(t))
        except asyncio.CancelledError:
            pass

        if active:
            await asyncio.gather(*active)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get system performance statistics."""
        return {
            "total_contracts_processed": self.total_contracts_processed,
            "successful_analyses": self.successful_analyses,
            "success_rate": self.successful_analyses / max(self.total_contracts_processed, 1),
            "total_exploits_found": self.total_exploits_found,
            "average_exploits_per_contract": self.total_exploits_found / max(self.total_contracts_processed, 1),
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.total_execution_time / max(self.total_contracts_processed, 1),
            "active_sessions": len(self.active_sessions),
            "system_uptime": time.time() - getattr(self, 'start_time', time.time())
        }
    
    async def shutdown(self):
        """Gracefully shutdown the system."""
        logger.info("Shutting down A1 Agentic System...")
        
        try:
            if self.active_sessions:
                logger.info(f"Waiting for {len(self.active_sessions)} active sessions to complete...")
                for session_id in list(self.active_sessions.keys()):
                    await self._cleanup_session(session_id)
                self.active_sessions.clear()
            
            if self.dex_router:
                await self.dex_router.close()
            
            if self.token_utils:
                await self.token_utils.close()
            
            if self.scanner:
                await self.scanner.close()
            
            if self.blockchain_client:
                await self.blockchain_client.__aexit__(None, None, None)
            
            if self.forge:
                await self.forge.cleanup()
            
            if self.result_storage:
                await self.result_storage.close()
            
            logger.info("A1 Agentic System shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def load_targets_from_file(file_path: str) -> List[ContractTarget]:
    """Load contract targets from file."""
    targets = []
    
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 2:
                    logger.warning(f"Invalid line {line_num} in {file_path}: {line}")
                    continue
                
                address = parts[0]
                network = parts[1]
                name = parts[2] if len(parts) > 2 else None
                priority = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
                
                targets.append(ContractTarget(
                    address=address,
                    network=network,
                    name=name,
                    priority=priority
                ))
        
        logger.info(f"Loaded {len(targets)} contract targets from {file_path}")
        return targets
        
    except Exception as e:
        logger.error(f"Failed to load targets from {file_path}: {e}")
        return []


async def main():
    """Main entry point for the A1 Agentic System."""
    parser = argparse.ArgumentParser(description="A1 Agentic System - Autonomous Smart Contract Exploit Generation")
    
    parser.add_argument('--config', '-c', default='.env', help='Configuration file path')
    parser.add_argument('--queue-url', help='AMQP URL for the contract queue')
    parser.add_argument('--queue-name', default='contract_targets', help='Queue name')
    parser.add_argument('--contract', help='Single contract address to analyze')
    parser.add_argument('--network', default='ethereum', help='Network name (ethereum, bsc)')
    parser.add_argument('--max-concurrent', type=int, default=3, help='Maximum concurrent executions')
    parser.add_argument('--output', '-o', help='Output file for results')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--force', action='store_true', help='Force re-analysis even if cached results exist')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    config_manager = ConfigurationManager(args.config)
    config = config_manager.get_config()
    
    processor = ContractProcessor(config)
    
    try:
        await processor.initialize()

        if args.contract:
            target = ContractTarget(
                address=args.contract,
                network=args.network,
                name=f"Manual_{args.contract[:8]}"
            )
            logger.info("Processing single contract...")
            result = await processor.process_contract(target, force=args.force)

            if args.output:
                output_data = {
                    "timestamp": datetime.now().isoformat(),
                    "results": [asdict(result)],
                    "performance_stats": processor.get_performance_stats()
                }
                with open(args.output, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output}")

            return 0

        if not args.queue_url:
            logger.error("No contract or queue specified. Provide --contract or --queue-url")
            return 1

        queue = ContractQueue(args.queue_url, args.queue_name)
        await queue.connect()

        logger.info("Processing contracts from queue... press Ctrl+C to stop")
        await processor.process_queue(queue, args.max_concurrent, force=args.force)
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        return 1
    except Exception as e:
        logger.error(f"System error: {e}")
        return 1
    finally:
        await processor.shutdown()


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
