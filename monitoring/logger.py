"""
System Logger - A1 Agentic System

Advanced logging system with structured logging, performance tracking,
and comprehensive audit trails.
"""

import logging
import logging.handlers
import json
import time
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import traceback

class SystemLogger:
    """
    Advanced system logger with structured logging capabilities.
    
    Provides comprehensive logging for the A1 system with performance
    tracking, audit trails, and structured log formatting.
    
    Features:
    - Structured JSON logging for machine parsing
    - Separate log files for system, performance, audit, and errors
    - Rotating file handlers to manage disk space
    - Console output for development
    - Performance tracking integration
    - Exception handling and stack traces
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize system logger.
        
        Args:
            config: Configuration dictionary with logging settings
        """
        self.config = config
        
        self.log_level = getattr(logging, config.get('LOG_LEVEL', 'INFO').upper())
        self.log_dir = Path(config.get('LOG_DIR', 'logs'))
        self.log_dir.mkdir(exist_ok=True)
        
        self.log_counts = {
            'debug': 0,
            'info': 0,
            'warning': 0,
            'error': 0,
            'critical': 0
        }
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Setup various loggers for different purposes."""
        
        self.system_logger = logging.getLogger('a1_system')
        self.system_logger.setLevel(self.log_level)
        
        self.performance_logger = logging.getLogger('a1_performance')
        self.performance_logger.setLevel(logging.INFO)
        
        self.audit_logger = logging.getLogger('a1_audit')
        self.audit_logger.setLevel(logging.INFO)
        
        self.error_logger = logging.getLogger('a1_errors')
        self.error_logger.setLevel(logging.ERROR)
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup log handlers."""
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        system_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'system.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        system_handler.setLevel(self.log_level)
        
        performance_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'performance.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        
        audit_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'audit.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'errors.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        
        json_formatter = JsonFormatter()
        
        system_handler.setFormatter(json_formatter)
        performance_handler.setFormatter(json_formatter)
        audit_handler.setFormatter(json_formatter)
        error_handler.setFormatter(json_formatter)
        
        self.system_logger.addHandler(console_handler)
        self.system_logger.addHandler(system_handler)

        self.performance_logger.addHandler(performance_handler)
        self.audit_logger.addHandler(audit_handler)
        self.error_logger.addHandler(error_handler)
    
    def log_agent_iteration(self, iteration: int, strategy: str, success: bool, execution_time: float, **kwargs):
        """Log agent iteration details for debugging and analysis."""
        self.performance_logger.info(
            "Agent iteration completed",
            extra={
                'iteration': iteration,
                'strategy': strategy,
                'success': success,
                'execution_time': execution_time,
                'event_type': 'agent_iteration',
                **kwargs
            }
        )
        self.log_counts['info'] += 1
    
    def log_tool_execution(self, tool_name: str, execution_time: float, success: bool, **kwargs):
        """Log tool execution for performance analysis."""
        self.system_logger.info(
            f"Tool {tool_name} executed",
            extra={
                'tool_name': tool_name,
                'execution_time': execution_time,
                'success': success,
                'event_type': 'tool_execution',
                **kwargs
            }
        )
        self.log_counts['info'] += 1
    
    def log_exploit_generation(self, contract_address: str, exploits_found: int, profit_potential: float, **kwargs):
        """Log exploit generation results."""
        self.audit_logger.info(
            "Exploit generation completed",
            extra={
                'contract_address': contract_address,
                'exploits_found': exploits_found,
                'profit_potential': profit_potential,
                'event_type': 'exploit_generation',
                **kwargs
            }
        )
        self.log_counts['info'] += 1
    
    def log_validation_result(self, code_hash: str, validation_success: bool, issues_count: int, **kwargs):
        """Log code validation results."""
        self.system_logger.info(
            "Code validation completed",
            extra={
                'code_hash': code_hash,
                'validation_success': validation_success,
                'issues_count': issues_count,
                'event_type': 'validation',
                **kwargs
            }
        )
        self.log_counts['info'] += 1
    
    def log_error(self, error_message: str, exception: Optional[Exception] = None, **kwargs):
        """Log errors with full context."""
        self.error_logger.error(
            error_message,
            extra={
                'event_type': 'error',
                'exception_type': type(exception).__name__ if exception else None,
                **kwargs
            },
            exc_info=exception
        )
        self.log_counts['error'] += 1

    def log_execution(self, strategy_id: str, tx_hashes: List[str], gas_used: int,
                      profit: float, max_gas: int, min_profit: float):
        """Log mainnet execution attempts and safety check results."""
        self.audit_logger.info(
            "Mainnet execution attempt",
            extra={
                'event_type': 'mainnet_execution',
                'strategy_id': strategy_id,
                'tx_hashes': tx_hashes,
                'gas_used': gas_used,
                'profit': profit,
                'max_gas': max_gas,
                'min_profit': min_profit,
                'gas_check_passed': gas_used <= max_gas,
                'profit_check_passed': profit >= min_profit
            }
        )
        self.log_counts['info'] += 1
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            'log_counts': self.log_counts.copy(),
            'total_logs': sum(self.log_counts.values()),
            'log_level': logging.getLevelName(self.log_level),
            'log_directory': str(self.log_dir)
        }


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_entry['exception'] = traceback.format_exception(*record.exc_info)
        
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)
