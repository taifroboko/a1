"""
Feedback Processor - A1 Agentic System

Processes binary profitability indicators, execution traces, and revert reasons
to provide intelligent feedback for strategy refinement and agent learning.
Implements advanced trace analysis and pattern recognition for exploit optimization.

Based on the A1 research paper specifications.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from decimal import Decimal
import time
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """Types of feedback signals"""
    PROFITABILITY = "profitability"
    EXECUTION_TRACE = "execution_trace"
    REVERT_REASON = "revert_reason"
    GAS_ANALYSIS = "gas_analysis"
    STATE_CHANGE = "state_change"
    ECONOMIC_IMPACT = "economic_impact"

class FeedbackSeverity(Enum):
    """Severity levels for feedback"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class FeedbackSignal:
    """Container for individual feedback signals"""
    signal_id: str
    feedback_type: FeedbackType
    severity: FeedbackSeverity
    message: str
    data: Dict[str, Any]
    timestamp: int
    source_tool: str
    strategy_id: Optional[str] = None
    iteration: Optional[int] = None

@dataclass
class FeedbackSummary:
    """Container for aggregated feedback summary"""
    summary_id: str
    strategy_id: str
    iteration: int
    total_signals: int
    critical_issues: int
    success_probability: float
    profit_potential: Decimal
    recommended_actions: List[str]
    pattern_insights: List[str]
    optimization_suggestions: List[str]

class FeedbackProcessor:
    """
    Advanced feedback processor for exploit strategy refinement.
    
    Processes execution traces, profitability indicators, and revert reasons
    to provide intelligent feedback for strategy optimization and agent learning.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the feedback processor.
        
        Args:
            config: Configuration dictionary with processing settings
        """
        self.config = config
        
        self.feedback_signals: List[FeedbackSignal] = []
        
        self.revert_patterns: Dict[str, int] = defaultdict(int)
        self.success_patterns: Dict[str, int] = defaultdict(int)
        self.gas_optimization_patterns: Dict[str, List[int]] = defaultdict(list)
        self.profit_correlation_patterns: Dict[str, List[float]] = defaultdict(list)
        
        self.min_confidence_threshold = config.get('MIN_CONFIDENCE_THRESHOLD', 0.6)
        self.max_feedback_history = config.get('MAX_FEEDBACK_HISTORY', 1000)
        self.pattern_recognition_window = config.get('PATTERN_RECOGNITION_WINDOW', 50)
        
        self.revert_reason_patterns = self._initialize_revert_patterns()
        
        self.economic_impact_thresholds = {
            'high_impact': 10000,  # $10k+
            'medium_impact': 1000,  # $1k+
            'low_impact': 100      # $100+
        }
    
    def _initialize_revert_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize known revert reason patterns and their classifications."""
        return {
            'insufficient_balance': {
                'patterns': [
                    r'insufficient.*balance',
                    r'transfer amount exceeds balance',
                    r'ERC20: transfer amount exceeds balance'
                ],
                'classification': 'balance_check',
                'severity': FeedbackSeverity.HIGH,
                'suggestions': [
                    'Check token balance before transfer',
                    'Implement balance validation',
                    'Consider flash loan for capital requirements'
                ]
            },
            'access_control': {
                'patterns': [
                    r'Ownable: caller is not the owner',
                    r'AccessControl:.*missing role',
                    r'unauthorized',
                    r'not authorized'
                ],
                'classification': 'permission_denied',
                'severity': FeedbackSeverity.CRITICAL,
                'suggestions': [
                    'Identify privilege escalation vectors',
                    'Check for access control bypasses',
                    'Analyze role-based permissions'
                ]
            },
            'reentrancy_guard': {
                'patterns': [
                    r'ReentrancyGuard: reentrant call',
                    r'reentrancy.*detected',
                    r'already.*entered'
                ],
                'classification': 'reentrancy_protection',
                'severity': FeedbackSeverity.MEDIUM,
                'suggestions': [
                    'Find alternative attack vectors',
                    'Check for cross-function reentrancy',
                    'Analyze state changes before external calls'
                ]
            }
        }
    
    async def process_execution_feedback(self, execution_result: Dict[str, Any], strategy_id: str, iteration: int) -> FeedbackSummary:
        """
        Process comprehensive execution feedback from strategy execution.
        
        Args:
            execution_result: Results from strategy execution
            strategy_id: ID of the executed strategy
            iteration: Current iteration number
            
        Returns:
            Comprehensive feedback summary with recommendations
        """
        logger.info(f"Processing execution feedback for strategy {strategy_id}, iteration {iteration}")
        
        feedback_signals = []
        
        if 'profitability' in execution_result:
            profitability_signals = await self._process_profitability_feedback(
                execution_result['profitability'], strategy_id, iteration
            )
            feedback_signals.extend(profitability_signals)
        
        if 'execution_traces' in execution_result:
            trace_signals = await self._process_execution_traces(
                execution_result['execution_traces'], strategy_id, iteration
            )
            feedback_signals.extend(trace_signals)
        
        if 'revert_reasons' in execution_result:
            revert_signals = await self._process_revert_reasons(
                execution_result['revert_reasons'], strategy_id, iteration
            )
            feedback_signals.extend(revert_signals)
        
        self.feedback_signals.extend(feedback_signals)
        
        summary = await self._generate_feedback_summary(feedback_signals, strategy_id, iteration)
        
        await self._update_pattern_recognition(feedback_signals, execution_result)
        
        self._cleanup_feedback_history()
        
        return summary
    
    async def _process_profitability_feedback(self, profitability_data: Dict[str, Any], strategy_id: str, iteration: int) -> List[FeedbackSignal]:
        """Process profitability indicators and generate feedback signals."""
        signals = []
        
        expected_profit = Decimal(str(profitability_data.get('expected_profit_usd', 0)))
        actual_profit = Decimal(str(profitability_data.get('actual_profit_usd', 0))) if profitability_data.get('actual_profit_usd') is not None else None
        gas_cost = Decimal(str(profitability_data.get('gas_cost_usd', 0)))
        
        if actual_profit is not None:
            if actual_profit > 0:
                severity = FeedbackSeverity.INFO if actual_profit < 100 else FeedbackSeverity.MEDIUM
                if actual_profit > 1000:
                    severity = FeedbackSeverity.HIGH
                
                signals.append(FeedbackSignal(
                    signal_id=f"profit_positive_{int(time.time())}",
                    feedback_type=FeedbackType.PROFITABILITY,
                    severity=severity,
                    message=f"Strategy generated profit: ${actual_profit:.2f}",
                    data={
                        'actual_profit': float(actual_profit),
                        'expected_profit': float(expected_profit),
                        'profit_ratio': float(actual_profit / max(expected_profit, Decimal('0.01')))
                    },
                    timestamp=int(time.time()),
                    source_tool='feedback_processor',
                    strategy_id=strategy_id,
                    iteration=iteration
                ))
            else:
                signals.append(FeedbackSignal(
                    signal_id=f"profit_negative_{int(time.time())}",
                    feedback_type=FeedbackType.PROFITABILITY,
                    severity=FeedbackSeverity.HIGH,
                    message=f"Strategy resulted in loss: ${actual_profit:.2f}",
                    data={
                        'actual_profit': float(actual_profit),
                        'expected_profit': float(expected_profit),
                        'loss_amount': float(abs(actual_profit))
                    },
                    timestamp=int(time.time()),
                    source_tool='feedback_processor',
                    strategy_id=strategy_id,
                    iteration=iteration
                ))
        
        return signals
    
    async def _process_execution_traces(self, traces_data: List[Dict[str, Any]], strategy_id: str, iteration: int) -> List[FeedbackSignal]:
        """Process execution traces and generate feedback signals."""
        signals = []
        
        for trace_data in traces_data:
            gas_used = trace_data.get('gas_used', 0)
            gas_limit = trace_data.get('gas_limit', 0)
            
            if gas_limit > 0:
                gas_efficiency = gas_used / gas_limit
                
                if gas_efficiency > 0.9:  # Very high gas usage
                    signals.append(FeedbackSignal(
                        signal_id=f"gas_high_{int(time.time())}",
                        feedback_type=FeedbackType.GAS_ANALYSIS,
                        severity=FeedbackSeverity.MEDIUM,
                        message=f"High gas usage: {gas_efficiency:.1%} of limit",
                        data={
                            'gas_used': gas_used,
                            'gas_limit': gas_limit,
                            'efficiency': gas_efficiency,
                            'tx_hash': trace_data.get('tx_hash', '')
                        },
                        timestamp=int(time.time()),
                        source_tool='feedback_processor',
                        strategy_id=strategy_id,
                        iteration=iteration
                    ))
        
        return signals
    
    async def _process_revert_reasons(self, revert_data: List[Dict[str, Any]], strategy_id: str, iteration: int) -> List[FeedbackSignal]:
        """Process revert reasons and generate feedback signals."""
        signals = []
        
        for revert_info in revert_data:
            revert_reason = revert_info.get('reason', '')
            tx_hash = revert_info.get('tx_hash', '')
            
            classification = self._classify_revert_reason(revert_reason)
            
            signals.append(FeedbackSignal(
                signal_id=f"revert_{int(time.time())}",
                feedback_type=FeedbackType.REVERT_REASON,
                severity=classification['severity'],
                message=f"Transaction reverted: {classification['type']} - {revert_reason[:100]}",
                data={
                    'revert_reason': revert_reason,
                    'classification': classification,
                    'tx_hash': tx_hash,
                    'suggested_fixes': classification['suggestions']
                },
                timestamp=int(time.time()),
                source_tool='feedback_processor',
                strategy_id=strategy_id,
                iteration=iteration
            ))
            
            self.revert_patterns[classification['pattern']] += 1
        
        return signals
    
    def _classify_revert_reason(self, revert_reason: str) -> Dict[str, Any]:
        """Classify revert reason and provide suggestions."""
        classification = {
            'type': 'unknown',
            'pattern': 'unknown',
            'severity': FeedbackSeverity.MEDIUM,
            'suggestions': ['Analyze contract logic for failure conditions']
        }
        
        revert_lower = revert_reason.lower()
        
        for pattern_name, pattern_info in self.revert_reason_patterns.items():
            for pattern in pattern_info['patterns']:
                if re.search(pattern, revert_lower):
                    classification.update({
                        'type': pattern_info['classification'],
                        'pattern': pattern_name,
                        'severity': pattern_info['severity'],
                        'suggestions': pattern_info['suggestions']
                    })
                    return classification
        
        if any(keyword in revert_lower for keyword in ['balance', 'insufficient', 'transfer']):
            classification.update({
                'type': 'balance_related',
                'pattern': 'balance_issue',
                'severity': FeedbackSeverity.HIGH,
                'suggestions': ['Check token balances and allowances', 'Verify transfer amounts']
            })
        
        return classification
    
    async def _generate_feedback_summary(self, feedback_signals: List[FeedbackSignal], strategy_id: str, iteration: int) -> FeedbackSummary:
        """Generate comprehensive feedback summary from all signals."""
        
        critical_issues = len([s for s in feedback_signals if s.severity == FeedbackSeverity.CRITICAL])
        
        success_probability = self._calculate_success_probability(feedback_signals, strategy_id)
        
        profit_potential = self._estimate_profit_potential(feedback_signals, strategy_id)
        
        recommended_actions = self._generate_recommendations(feedback_signals, strategy_id)
        
        pattern_insights = self._extract_pattern_insights(feedback_signals, strategy_id)
        
        optimization_suggestions = self._generate_optimization_suggestions(feedback_signals, strategy_id)
        
        return FeedbackSummary(
            summary_id=f"summary_{int(time.time())}_{strategy_id}",
            strategy_id=strategy_id,
            iteration=iteration,
            total_signals=len(feedback_signals),
            critical_issues=critical_issues,
            success_probability=success_probability,
            profit_potential=profit_potential,
            recommended_actions=recommended_actions,
            pattern_insights=pattern_insights,
            optimization_suggestions=optimization_suggestions
        )
    
    def _calculate_success_probability(self, feedback_signals: List[FeedbackSignal], strategy_id: str) -> float:
        """Calculate success probability based on feedback signals."""
        base_probability = 0.5  # Start with neutral probability
        
        for signal in feedback_signals:
            if signal.severity == FeedbackSeverity.CRITICAL:
                base_probability -= 0.2
            elif signal.severity == FeedbackSeverity.HIGH:
                base_probability -= 0.1
            elif signal.severity == FeedbackSeverity.MEDIUM:
                base_probability -= 0.05
            elif signal.feedback_type == FeedbackType.PROFITABILITY and 'positive' in signal.signal_id:
                base_probability += 0.15
        
        return max(0.0, min(1.0, base_probability))
    
    def _estimate_profit_potential(self, feedback_signals: List[FeedbackSignal], strategy_id: str) -> Decimal:
        """Estimate profit potential based on feedback signals."""
        profit_potential = Decimal('0')
        
        for signal in feedback_signals:
            if signal.feedback_type == FeedbackType.PROFITABILITY:
                actual_profit = signal.data.get('actual_profit', 0)
                if actual_profit > 0:
                    profit_potential = max(profit_potential, Decimal(str(actual_profit)))
        
        return profit_potential
    
    def _generate_recommendations(self, feedback_signals: List[FeedbackSignal], strategy_id: str) -> List[str]:
        """Generate actionable recommendations based on feedback."""
        recommendations = []
        
        signal_groups = defaultdict(list)
        for signal in feedback_signals:
            signal_groups[signal.feedback_type].append(signal)
        
        if FeedbackType.PROFITABILITY in signal_groups:
            profit_signals = signal_groups[FeedbackType.PROFITABILITY]
            negative_profits = [s for s in profit_signals if 'negative' in s.signal_id]
            
            if negative_profits:
                recommendations.append("Strategy resulted in losses - consider alternative attack vectors")
                recommendations.append("Analyze market conditions and timing for better execution")
        
        if FeedbackType.GAS_ANALYSIS in signal_groups:
            gas_signals = signal_groups[FeedbackType.GAS_ANALYSIS]
            high_gas_signals = [s for s in gas_signals if s.severity in [FeedbackSeverity.HIGH, FeedbackSeverity.MEDIUM]]
            
            if high_gas_signals:
                recommendations.append("Optimize gas usage through transaction batching")
                recommendations.append("Consider alternative execution paths with lower gas costs")
        
        if FeedbackType.REVERT_REASON in signal_groups:
            revert_signals = signal_groups[FeedbackType.REVERT_REASON]
            
            for signal in revert_signals:
                suggestions = signal.data.get('suggested_fixes', [])
                recommendations.extend(suggestions[:2])  # Top 2 suggestions per revert
        
        unique_recommendations = list(dict.fromkeys(recommendations))
        return unique_recommendations[:8]  # Top 8 recommendations
    
    def _extract_pattern_insights(self, feedback_signals: List[FeedbackSignal], strategy_id: str) -> List[str]:
        """Extract pattern insights from feedback analysis."""
        insights = []
        
        recent_reverts = [s for s in feedback_signals if s.feedback_type == FeedbackType.REVERT_REASON]
        if recent_reverts:
            revert_types = [s.data.get('classification', {}).get('pattern', 'unknown') for s in recent_reverts]
            most_common_revert = Counter(revert_types).most_common(1)[0][0] if revert_types else None
            
            if most_common_revert and most_common_revert != 'unknown':
                insights.append(f"Most common failure pattern: {most_common_revert}")
        
        strategy_signals = [s for s in self.feedback_signals if s.strategy_id == strategy_id]
        if len(strategy_signals) > 5:
            success_rate = len([s for s in strategy_signals if s.severity == FeedbackSeverity.INFO]) / len(strategy_signals)
            if success_rate > 0.7:
                insights.append("Strategy shows consistent success pattern")
            elif success_rate < 0.3:
                insights.append("Strategy shows consistent failure pattern")
        
        return insights[:5]  # Top 5 insights
    
    def _generate_optimization_suggestions(self, feedback_signals: List[FeedbackSignal], strategy_id: str) -> List[str]:
        """Generate optimization suggestions based on feedback analysis."""
        suggestions = []
        
        gas_signals = [s for s in feedback_signals if s.feedback_type == FeedbackType.GAS_ANALYSIS]
        if gas_signals:
            high_gas_signals = [s for s in gas_signals if 'high' in s.signal_id or 'inefficient' in s.signal_id]
            if high_gas_signals:
                suggestions.append("Implement gas optimization techniques (batching, efficient opcodes)")
                suggestions.append("Consider using CREATE2 for deterministic contract deployment")
        
        profit_signals = [s for s in feedback_signals if s.feedback_type == FeedbackType.PROFITABILITY]
        if profit_signals:
            low_profit_signals = [s for s in profit_signals if s.data.get('actual_profit', 0) < 100]
            if low_profit_signals:
                suggestions.append("Increase position size or find higher-value targets")
                suggestions.append("Optimize timing to capture maximum price movements")
        
        return suggestions[:6]  # Top 6 suggestions
    
    async def _update_pattern_recognition(self, feedback_signals: List[FeedbackSignal], execution_result: Dict[str, Any]):
        """Update pattern recognition based on new feedback."""
        
        success_indicators = [
            s for s in feedback_signals 
            if s.feedback_type == FeedbackType.PROFITABILITY and 'positive' in s.signal_id
        ]
        
        if success_indicators:
            execution_pattern = self._extract_execution_pattern(execution_result)
            self.success_patterns[execution_pattern] += 1
        
        for signal in feedback_signals:
            if signal.feedback_type == FeedbackType.PROFITABILITY and signal.strategy_id:
                actual_profit = signal.data.get('actual_profit', 0)
                if actual_profit > 0:
                    self.profit_correlation_patterns[signal.strategy_id].append(actual_profit)
                    
                    if len(self.profit_correlation_patterns[signal.strategy_id]) > self.pattern_recognition_window:
                        self.profit_correlation_patterns[signal.strategy_id] = self.profit_correlation_patterns[signal.strategy_id][-self.pattern_recognition_window:]
    
    def _extract_execution_pattern(self, execution_result: Dict[str, Any]) -> str:
        """Extract execution pattern signature for pattern recognition."""
        pattern_elements = []
        
        gas_data = execution_result.get('gas_analysis', {})
        total_gas = gas_data.get('total_gas_used', 0)
        
        if total_gas > 0:
            if total_gas < 100000:
                pattern_elements.append('low_gas')
            elif total_gas < 500000:
                pattern_elements.append('medium_gas')
            else:
                pattern_elements.append('high_gas')
        
        profitability = execution_result.get('profitability', {})
        actual_profit = profitability.get('actual_profit_usd', 0)
        
        if actual_profit > 1000:
            pattern_elements.append('high_profit')
        elif actual_profit > 100:
            pattern_elements.append('medium_profit')
        elif actual_profit > 0:
            pattern_elements.append('low_profit')
        else:
            pattern_elements.append('no_profit')
        
        return '_'.join(pattern_elements) if pattern_elements else 'unknown_pattern'
    
    def _cleanup_feedback_history(self):
        """Clean up old feedback history to maintain performance."""
        if len(self.feedback_signals) > self.max_feedback_history:
            self.feedback_signals = self.feedback_signals[-self.max_feedback_history:]
    
    async def get_feedback_analytics(self, strategy_id: Optional[str] = None, time_window: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive feedback analytics.
        
        Args:
            strategy_id: Optional strategy ID to filter analytics
            time_window: Optional time window in seconds for recent analytics
            
        Returns:
            Comprehensive analytics dictionary
        """
        current_time = int(time.time())
        
        filtered_signals = self.feedback_signals
        
        if strategy_id:
            filtered_signals = [s for s in filtered_signals if s.strategy_id == strategy_id]
        
        if time_window:
            cutoff_time = current_time - time_window
            filtered_signals = [s for s in filtered_signals if s.timestamp >= cutoff_time]
        
        if not filtered_signals:
            return {'message': 'No feedback data available for the specified criteria'}
        
        analytics = {
            'summary': {
                'total_signals': len(filtered_signals),
                'time_range': {
                    'start': min(s.timestamp for s in filtered_signals),
                    'end': max(s.timestamp for s in filtered_signals)
                },
                'strategy_coverage': len(set(s.strategy_id for s in filtered_signals if s.strategy_id))
            },
            'signal_distribution': {},
            'severity_distribution': {},
            'success_metrics': {},
            'pattern_analysis': {}
        }
        
        signal_types = [s.feedback_type.value for s in filtered_signals]
        analytics['signal_distribution'] = dict(Counter(signal_types))
        
        severities = [s.severity.value for s in filtered_signals]
        analytics['severity_distribution'] = dict(Counter(severities))
        
        profit_signals = [s for s in filtered_signals if s.feedback_type == FeedbackType.PROFITABILITY]
        if profit_signals:
            positive_profits = [s for s in profit_signals if 'positive' in s.signal_id]
            analytics['success_metrics'] = {
                'profit_success_rate': len(positive_profits) / len(profit_signals),
                'total_profit_signals': len(profit_signals),
                'positive_profit_signals': len(positive_profits)
            }
        
        return analytics
