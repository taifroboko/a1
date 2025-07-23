"""
Validation Engine - A1 Agentic System

Comprehensive validation engine for generated exploit contracts before execution.
Validates syntax, security, and Forge compatibility.

Based on the A1 research paper specifications.
"""

import asyncio
import subprocess
import tempfile
import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import time
import re

from parsers.solidity_parser import CodeBlock, CodeBlockType

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"           # Basic syntax and structure
    STANDARD = "standard"     # Standard + security checks
    STRICT = "strict"         # Standard + advanced analysis
    FORGE_ONLY = "forge_only" # Only Forge compilation

class ValidationStatus(Enum):
    """Validation status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

@dataclass
class ValidationIssue:
    """Individual validation issue"""
    level: str  # error, warning, info
    message: str
    line_number: Optional[int]
    column: Optional[int]
    rule: str
    suggestion: Optional[str]

@dataclass
class ValidationResult:
    """Result of validation process"""
    success: bool
    status: ValidationStatus
    validation_level: ValidationLevel
    issues: List[ValidationIssue]
    compilation_success: bool
    forge_compatible: bool
    gas_estimate: Optional[int]
    execution_time: float
    metadata: Dict[str, Any]
    validated_code: str
    error_message: Optional[str]

class ValidationEngine:
    """
    Advanced validation engine for exploit contract verification.
    
    Provides comprehensive validation including syntax checking, security analysis,
    Forge compatibility testing, and gas estimation before execution.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize validation engine.
        
        Args:
            config: Configuration dictionary with validation settings
        """
        self.config = config
        
        self.validation_level = ValidationLevel(config.get('VALIDATION_LEVEL', 'standard'))
        self.enable_forge_validation = config.get('ENABLE_FORGE_VALIDATION', True)
        self.enable_security_checks = config.get('ENABLE_SECURITY_CHECKS', True)
        self.enable_gas_estimation = config.get('ENABLE_GAS_ESTIMATION', True)
        self.max_validation_time = config.get('MAX_VALIDATION_TIME', 60)  # seconds
        
        self.forge_timeout = config.get('FORGE_TIMEOUT', 30)
        self.forge_profile = config.get('FORGE_PROFILE', 'default')
        
        self.security_rules = self._load_security_rules()
        
        self.total_validations = 0
        self.successful_validations = 0
        self.validation_errors = 0
        
        self.temp_dir = Path(tempfile.mkdtemp(prefix='a1_validation_'))
        self.temp_dir.mkdir(exist_ok=True)
    
    def _load_security_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load security validation rules."""
        return {
            'reentrancy': {
                'pattern': r'\.call\s*\{[^}]*\}\s*\([^)]*\)',
                'level': 'error',
                'message': 'Potential reentrancy vulnerability detected',
                'suggestion': 'Use checks-effects-interactions pattern'
            },
            'unchecked_call': {
                'pattern': r'\.call\s*\([^)]*\)(?!\s*;?\s*require)',
                'level': 'warning',
                'message': 'Unchecked external call',
                'suggestion': 'Check return value of external calls'
            },
            'tx_origin': {
                'pattern': r'tx\.origin',
                'level': 'error',
                'message': 'Use of tx.origin for authorization',
                'suggestion': 'Use msg.sender instead of tx.origin'
            },
            'delegatecall': {
                'pattern': r'\.delegatecall\s*\(',
                'level': 'warning',
                'message': 'Use of delegatecall detected',
                'suggestion': 'Ensure delegatecall target is trusted'
            },
            'selfdestruct': {
                'pattern': r'selfdestruct\s*\(',
                'level': 'warning',
                'message': 'Use of selfdestruct detected',
                'suggestion': 'Consider security implications of selfdestruct'
            },
            'block_timestamp': {
                'pattern': r'block\.timestamp|now\b',
                'level': 'info',
                'message': 'Use of block.timestamp for logic',
                'suggestion': 'Be aware of miner manipulation possibilities'
            },
            'unsafe_math': {
                'pattern': r'(?<!\busing\s+SafeMath\s+for\s+uint256\s*;)[\+\-\*\/]\s*(?=\w)',
                'level': 'warning',
                'message': 'Potential integer overflow/underflow',
                'suggestion': 'Use SafeMath or Solidity 0.8+ built-in checks'
            }
        }
    
    async def validate(self, code_block: CodeBlock) -> ValidationResult:
        """
        Validate a code block comprehensively.
        
        Args:
            code_block: Code block to validate
            
        Returns:
            Validation result
        """
        start_time = time.time()
        
        try:
            self.total_validations += 1
            
            result = ValidationResult(
                success=False,
                status=ValidationStatus.FAILED,
                validation_level=self.validation_level,
                issues=[],
                compilation_success=False,
                forge_compatible=False,
                gas_estimate=None,
                execution_time=0.0,
                metadata={},
                validated_code=code_block.content,
                error_message=None
            )
            
            if code_block.block_type != CodeBlockType.SOLIDITY:
                result.status = ValidationStatus.SKIPPED
                result.error_message = "Not a Solidity code block"
                return result
            
            logger.debug("Phase 1: Basic syntax validation")
            syntax_issues = await self._validate_syntax(code_block.content)
            result.issues.extend(syntax_issues)
            
            if self.enable_security_checks and self.validation_level != ValidationLevel.FORGE_ONLY:
                logger.debug("Phase 2: Security validation")
                security_issues = await self._validate_security(code_block.content)
                result.issues.extend(security_issues)
            
            if self.enable_forge_validation:
                logger.debug("Phase 3: Forge compilation validation")
                forge_result = await self._validate_with_forge(code_block.content)
                result.compilation_success = forge_result['success']
                result.forge_compatible = forge_result['forge_compatible']
                if forge_result['issues']:
                    result.issues.extend(forge_result['issues'])
                if forge_result['gas_estimate']:
                    result.gas_estimate = forge_result['gas_estimate']
            
            if self.validation_level == ValidationLevel.STRICT:
                logger.debug("Phase 4: Advanced analysis")
                advanced_issues = await self._validate_advanced(code_block.content)
                result.issues.extend(advanced_issues)
            
            error_count = sum(1 for issue in result.issues if issue.level == 'error')
            warning_count = sum(1 for issue in result.issues if issue.level == 'warning')
            
            if error_count == 0:
                if self.enable_forge_validation:
                    result.success = result.compilation_success
                    result.status = ValidationStatus.PASSED if result.compilation_success else ValidationStatus.FAILED
                else:
                    result.success = True
                    result.status = ValidationStatus.WARNING if warning_count > 0 else ValidationStatus.PASSED
            else:
                result.success = False
                result.status = ValidationStatus.FAILED
            
            result.metadata = {
                'total_issues': len(result.issues),
                'error_count': error_count,
                'warning_count': warning_count,
                'info_count': sum(1 for issue in result.issues if issue.level == 'info'),
                'code_length': len(code_block.content),
                'validation_phases': self._get_validation_phases()
            }
            
            result.execution_time = time.time() - start_time
            
            if result.success:
                self.successful_validations += 1
            
            logger.info(f"Validation completed: {result.status.value} with {len(result.issues)} issues in {result.execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.validation_errors += 1
            error_msg = f"Validation failed: {str(e)}"
            logger.error(error_msg)
            
            return ValidationResult(
                success=False,
                status=ValidationStatus.FAILED,
                validation_level=self.validation_level,
                issues=[],
                compilation_success=False,
                forge_compatible=False,
                gas_estimate=None,
                execution_time=time.time() - start_time,
                metadata={},
                validated_code=code_block.content,
                error_message=error_msg
            )
    
    async def _validate_syntax(self, code: str) -> List[ValidationIssue]:
        """Validate basic Solidity syntax."""
        issues = []
        
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            
            if (line.endswith(')') and 
                not line.startswith('function') and 
                not line.startswith('modifier') and
                not line.startswith('if') and
                not line.startswith('for') and
                not line.startswith('while') and
                not line.endswith('{') and
                not line.endswith(';')):
                issues.append(ValidationIssue(
                    level='error',
                    message='Missing semicolon',
                    line_number=line_num,
                    column=len(line),
                    rule='syntax_semicolon',
                    suggestion='Add semicolon at end of statement'
                ))
            
            if line.count('(') != line.count(')'):
                issues.append(ValidationIssue(
                    level='error',
                    message='Unmatched parentheses',
                    line_number=line_num,
                    column=None,
                    rule='syntax_parentheses',
                    suggestion='Check parentheses matching'
                ))
            
            if 'function ' in line and 'public' not in line and 'private' not in line and 'internal' not in line and 'external' not in line:
                if not any(keyword in line for keyword in ['constructor', 'fallback', 'receive']):
                    issues.append(ValidationIssue(
                        level='warning',
                        message='Function missing visibility specifier',
                        line_number=line_num,
                        column=None,
                        rule='syntax_visibility',
                        suggestion='Add visibility specifier (public, private, internal, external)'
                    ))
        
        return issues
    
    async def _validate_security(self, code: str) -> List[ValidationIssue]:
        """Validate security aspects of the code."""
        issues = []
        
        for rule_name, rule_config in self.security_rules.items():
            pattern = rule_config['pattern']
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                issues.append(ValidationIssue(
                    level=rule_config['level'],
                    message=rule_config['message'],
                    line_number=line_num,
                    column=match.start() - code.rfind('\n', 0, match.start()),
                    rule=f'security_{rule_name}',
                    suggestion=rule_config['suggestion']
                ))
        
        return issues
    
    async def _validate_with_forge(self, code: str) -> Dict[str, Any]:
        """Validate code using Forge compilation."""
        result = {
            'success': False,
            'forge_compatible': False,
            'issues': [],
            'gas_estimate': None,
            'compilation_output': ''
        }
        
        try:
            temp_file = self.temp_dir / f"validation_{int(time.time())}.sol"
            
            prepared_code = self._prepare_code_for_forge(code)
            
            with open(temp_file, 'w') as f:
                f.write(prepared_code)
            
            cmd = ['forge', 'build', '--root', str(self.temp_dir)]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=self.forge_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                result['issues'].append(ValidationIssue(
                    level='error',
                    message='Forge compilation timeout',
                    line_number=None,
                    column=None,
                    rule='forge_timeout',
                    suggestion='Simplify code or increase timeout'
                ))
                return result
            
            stdout_str = stdout.decode('utf-8')
            stderr_str = stderr.decode('utf-8')
            result['compilation_output'] = stdout_str + stderr_str
            
            if process.returncode == 0:
                result['success'] = True
                result['forge_compatible'] = True
                
                if self.enable_gas_estimation:
                    gas_estimate = self._extract_gas_estimate(stdout_str)
                    if gas_estimate:
                        result['gas_estimate'] = gas_estimate
            else:
                forge_issues = self._parse_forge_errors(stderr_str)
                result['issues'].extend(forge_issues)
            
            if temp_file.exists():
                temp_file.unlink()
            
        except Exception as e:
            logger.error(f"Forge validation failed: {e}")
            result['issues'].append(ValidationIssue(
                level='error',
                message=f'Forge validation error: {str(e)}',
                line_number=None,
                column=None,
                rule='forge_error',
                suggestion='Check Forge installation and configuration'
            ))
        
        return result
    
    def _prepare_code_for_forge(self, code: str) -> str:
        """Prepare code for Forge compilation."""
        if 'pragma solidity' not in code.lower():
            code = 'pragma solidity ^0.8.0;\n\n' + code
        
        if 'import ' not in code and ('Test' in code or 'test' in code):
            code = 'pragma solidity ^0.8.0;\n\nimport "forge-std/Test.sol";\n\n' + code.replace('pragma solidity ^0.8.0;\n\n', '')
        
        return code
    
    def _extract_gas_estimate(self, output: str) -> Optional[int]:
        """Extract gas estimate from Forge output."""
        gas_patterns = [
            r'gas:\s*(\d+)',
            r'gas used:\s*(\d+)',
            r'execution gas:\s*(\d+)',
            r'total gas:\s*(\d+)'
        ]
        
        for pattern in gas_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _parse_forge_errors(self, stderr: str) -> List[ValidationIssue]:
        """Parse Forge compilation errors into validation issues."""
        issues = []
        
        lines = stderr.split('\n')
        current_error = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            error_match = re.match(r'Error\s*\((\d+)\):\s*(.*)', line)
            if error_match:
                error_code = error_match.group(1)
                message = error_match.group(2)
                
                issues.append(ValidationIssue(
                    level='error',
                    message=f'Compilation error: {message}',
                    line_number=None,
                    column=None,
                    rule=f'forge_error_{error_code}',
                    suggestion='Fix compilation error'
                ))
                continue
            
            warning_match = re.match(r'Warning\s*\((\d+)\):\s*(.*)', line)
            if warning_match:
                warning_code = warning_match.group(1)
                message = warning_match.group(2)
                
                issues.append(ValidationIssue(
                    level='warning',
                    message=f'Compilation warning: {message}',
                    line_number=None,
                    column=None,
                    rule=f'forge_warning_{warning_code}',
                    suggestion='Consider addressing warning'
                ))
                continue
            
            location_match = re.match(r'-->\s*([^:]+):(\d+):(\d+):', line)
            if location_match and issues:
                issues[-1].line_number = int(location_match.group(2))
                issues[-1].column = int(location_match.group(3))
        
        return issues
    
    async def _validate_advanced(self, code: str) -> List[ValidationIssue]:
        """Perform advanced code analysis."""
        issues = []
        
        complexity_issues = self._analyze_complexity(code)
        issues.extend(complexity_issues)
        
        pattern_issues = self._analyze_patterns(code)
        issues.extend(pattern_issues)
        
        best_practice_issues = self._check_best_practices(code)
        issues.extend(best_practice_issues)
        
        return issues
    
    def _analyze_complexity(self, code: str) -> List[ValidationIssue]:
        """Analyze code complexity."""
        issues = []
        
        function_count = len(re.findall(r'function\s+\w+', code, re.IGNORECASE))
        line_count = len(code.split('\n'))
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(code)
        
        if function_count > 20:
            issues.append(ValidationIssue(
                level='warning',
                message=f'High function count: {function_count}',
                line_number=None,
                column=None,
                rule='complexity_function_count',
                suggestion='Consider breaking into multiple contracts'
            ))
        
        if line_count > 500:
            issues.append(ValidationIssue(
                level='warning',
                message=f'High line count: {line_count}',
                line_number=None,
                column=None,
                rule='complexity_line_count',
                suggestion='Consider refactoring into smaller contracts'
            ))
        
        if cyclomatic_complexity > 10:
            issues.append(ValidationIssue(
                level='warning',
                message=f'High cyclomatic complexity: {cyclomatic_complexity}',
                line_number=None,
                column=None,
                rule='complexity_cyclomatic',
                suggestion='Simplify control flow'
            ))
        
        return issues
    
    def _calculate_cyclomatic_complexity(self, code: str) -> int:
        """Calculate cyclomatic complexity."""
        decision_keywords = ['if', 'else', 'for', 'while', 'case', '&&', '||', '?']
        complexity = 1  # Base complexity
        
        for keyword in decision_keywords:
            complexity += len(re.findall(rf'\b{keyword}\b', code, re.IGNORECASE))
        
        return complexity
    
    def _analyze_patterns(self, code: str) -> List[ValidationIssue]:
        """Analyze code patterns."""
        issues = []
        
        antipatterns = {
            'magic_numbers': {
                'pattern': r'\b\d{4,}\b',
                'message': 'Magic number detected',
                'suggestion': 'Use named constants'
            },
            'long_parameter_list': {
                'pattern': r'function\s+\w+\s*\([^)]{100,}\)',
                'message': 'Long parameter list',
                'suggestion': 'Consider using structs for parameters'
            },
            'deep_nesting': {
                'pattern': r'{\s*[^}]*{\s*[^}]*{\s*[^}]*{',
                'message': 'Deep nesting detected',
                'suggestion': 'Reduce nesting levels'
            }
        }
        
        for pattern_name, pattern_config in antipatterns.items():
            matches = re.finditer(pattern_config['pattern'], code, re.IGNORECASE | re.DOTALL)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    level='info',
                    message=pattern_config['message'],
                    line_number=line_num,
                    column=None,
                    rule=f'pattern_{pattern_name}',
                    suggestion=pattern_config['suggestion']
                ))
        
        return issues
    
    def _check_best_practices(self, code: str) -> List[ValidationIssue]:
        """Check Solidity best practices."""
        issues = []
        
        if 'function ' in code and '///' not in code and '/**' not in code:
            issues.append(ValidationIssue(
                level='info',
                message='Missing NatSpec documentation',
                line_number=None,
                column=None,
                rule='best_practice_natspec',
                suggestion='Add NatSpec documentation for functions'
            ))
        
        if '.call(' in code and 'require(' not in code and 'revert(' not in code:
            issues.append(ValidationIssue(
                level='warning',
                message='External calls without proper error handling',
                line_number=None,
                column=None,
                rule='best_practice_error_handling',
                suggestion='Add proper error handling for external calls'
            ))
        
        if 'function ' in code and 'event ' not in code:
            issues.append(ValidationIssue(
                level='info',
                message='No events defined',
                line_number=None,
                column=None,
                rule='best_practice_events',
                suggestion='Consider adding events for important state changes'
            ))
        
        return issues
    
    def _get_validation_phases(self) -> List[str]:
        """Get list of validation phases based on configuration."""
        phases = ['syntax']
        
        if self.enable_security_checks and self.validation_level != ValidationLevel.FORGE_ONLY:
            phases.append('security')
        
        if self.enable_forge_validation:
            phases.append('forge_compilation')
        
        if self.validation_level == ValidationLevel.STRICT:
            phases.append('advanced_analysis')
        
        return phases
    
    async def validate_multiple(self, code_blocks: List[CodeBlock]) -> List[ValidationResult]:
        """
        Validate multiple code blocks.
        
        Args:
            code_blocks: List of code blocks to validate
            
        Returns:
            List of validation results
        """
        results = []
        
        tasks = [self.validate(block) for block in code_blocks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Validation failed for block {i}: {result}")
                final_results.append(ValidationResult(
                    success=False,
                    status=ValidationStatus.FAILED,
                    validation_level=self.validation_level,
                    issues=[],
                    compilation_success=False,
                    forge_compatible=False,
                    gas_estimate=None,
                    execution_time=0.0,
                    metadata={},
                    validated_code=code_blocks[i].content if i < len(code_blocks) else '',
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get summary of validation results."""
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        total_issues = sum(len(r.issues) for r in results)
        error_count = sum(sum(1 for issue in r.issues if issue.level == 'error') for r in results)
        warning_count = sum(sum(1 for issue in r.issues if issue.level == 'warning') for r in results)
        
        return {
            'total_blocks': total,
            'passed': passed,
            'failed': failed,
            'success_rate': passed / max(total, 1),
            'total_issues': total_issues,
            'error_count': error_count,
            'warning_count': warning_count,
            'forge_compatible': sum(1 for r in results if r.forge_compatible),
            'average_execution_time': sum(r.execution_time for r in results) / max(total, 1)
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get validation engine performance statistics."""
        return {
            'total_validations': self.total_validations,
            'successful_validations': self.successful_validations,
            'validation_errors': self.validation_errors,
            'success_rate': self.successful_validations / max(self.total_validations, 1),
            'error_rate': self.validation_errors / max(self.total_validations, 1),
            'validation_level': self.validation_level.value,
            'forge_enabled': self.enable_forge_validation,
            'security_checks_enabled': self.enable_security_checks
        }
    
    async def cleanup(self):
        """Cleanup validation resources."""
        try:
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
            
            logger.info("Validation engine cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during validation cleanup: {e}")
