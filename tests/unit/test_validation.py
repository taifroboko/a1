"""
Unit Tests - Validation Engine

Test the validation engine for generated exploit contracts.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from validation.validator import ValidationEngine, ValidationResult, ValidationLevel, ValidationStatus
from parsers.solidity_parser import CodeBlock, CodeBlockType

class TestValidationEngine:
    """Test cases for ValidationEngine."""
    
    @pytest.fixture
    def validator(self, test_config):
        """Create validation engine instance."""
        config = test_config.copy()
        config['ENABLE_FORGE_VALIDATION'] = False  # Disable for unit tests
        return ValidationEngine(config)
    
    @pytest.fixture
    def sample_code_block(self, sample_solidity_code):
        """Create sample code block for testing."""
        return CodeBlock(
            content=sample_solidity_code,
            block_type=CodeBlockType.SOLIDITY,
            language='solidity',
            start_position=0,
            end_position=len(sample_solidity_code),
            line_start=1,
            line_end=sample_solidity_code.count('\n') + 1,
            metadata={'test': True},
            hash='test_hash_123'
        )
    
    @pytest.mark.asyncio
    async def test_validate_basic_syntax(self, validator, sample_code_block):
        """Test basic syntax validation."""
        result = await validator.validate(sample_code_block)
        
        assert isinstance(result, ValidationResult)
        assert result.validation_level == ValidationLevel.STANDARD
        assert len([issue for issue in result.issues if issue.level == 'error']) == 0
    
    @pytest.mark.asyncio
    async def test_validate_security_issues(self, validator):
        """Test security validation."""
        vulnerable_code = """
pragma solidity ^0.8.0;

contract VulnerableContract {
    function badFunction() external {
        // Using tx.origin (security issue)
        require(tx.origin == msg.sender);
        
        // Unchecked external call
        msg.sender.call("");
        
        // Reentrancy vulnerability
        msg.sender.call{value: 1 ether}("");
    }
}
"""
        
        code_block = CodeBlock(
            content=vulnerable_code,
            block_type=CodeBlockType.SOLIDITY,
            language='solidity',
            start_position=0,
            end_position=len(vulnerable_code),
            line_start=1,
            line_end=vulnerable_code.count('\n') + 1,
            metadata={},
            hash='vulnerable_hash'
        )
        
        result = await validator.validate(code_block)
        
        security_issues = [issue for issue in result.issues if 'security_' in issue.rule]
        assert len(security_issues) > 0
        
        issue_types = [issue.rule for issue in security_issues]
        assert any('tx_origin' in rule for rule in issue_types)
        assert any('unchecked_call' in rule for rule in issue_types)
    
    @pytest.mark.asyncio
    async def test_validate_syntax_errors(self, validator):
        """Test validation of code with syntax errors."""
        invalid_code = """
pragma solidity ^0.8.0;

contract InvalidContract {
    function badSyntax() external {
        // Missing semicolon
        uint256 x = 5
        
        // Unmatched parentheses
        require(x > 0;
    }
}
"""
        
        code_block = CodeBlock(
            content=invalid_code,
            block_type=CodeBlockType.SOLIDITY,
            language='solidity',
            start_position=0,
            end_position=len(invalid_code),
            line_start=1,
            line_end=invalid_code.count('\n') + 1,
            metadata={},
            hash='invalid_hash'
        )
        
        result = await validator.validate(code_block)
        
        syntax_errors = [issue for issue in result.issues if issue.level == 'error']
        assert len(syntax_errors) > 0
        assert not result.success
    
    @pytest.mark.asyncio
    async def test_validate_non_solidity_block(self, validator):
        """Test validation of non-Solidity code block."""
        python_code = """
def hello_world():
    print("Hello, World!")
"""
        
        code_block = CodeBlock(
            content=python_code,
            block_type=CodeBlockType.PYTHON,
            language='python',
            start_position=0,
            end_position=len(python_code),
            line_start=1,
            line_end=python_code.count('\n') + 1,
            metadata={},
            hash='python_hash'
        )
        
        result = await validator.validate(code_block)
        
        assert result.status == ValidationStatus.SKIPPED
        assert result.error_message == "Not a Solidity code block"
    
    @pytest.mark.asyncio
    async def test_validate_multiple_blocks(self, validator, sample_code_block):
        """Test validation of multiple code blocks."""
        code_blocks = [sample_code_block] * 3
        
        results = await validator.validate_multiple(code_blocks)
        
        assert len(results) == 3
        assert all(isinstance(result, ValidationResult) for result in results)
    
    def test_validation_summary(self, validator):
        """Test validation summary generation."""
        results = [
            ValidationResult(
                success=True,
                status=ValidationStatus.PASSED,
                validation_level=ValidationLevel.STANDARD,
                issues=[],
                compilation_success=True,
                forge_compatible=True,
                gas_estimate=21000,
                execution_time=0.1,
                metadata={},
                validated_code="test",
                error_message=None
            ),
            ValidationResult(
                success=False,
                status=ValidationStatus.FAILED,
                validation_level=ValidationLevel.STANDARD,
                issues=[Mock(level='error')],
                compilation_success=False,
                forge_compatible=False,
                gas_estimate=None,
                execution_time=0.2,
                metadata={},
                validated_code="test",
                error_message="Test error"
            )
        ]
        
        summary = validator.get_validation_summary(results)
        
        assert summary['total_blocks'] == 2
        assert summary['passed'] == 1
        assert summary['failed'] == 1
        assert summary['success_rate'] == 0.5
        assert summary['forge_compatible'] == 1
    
    def test_performance_stats(self, validator):
        """Test validation engine performance statistics."""
        validator.total_validations = 10
        validator.successful_validations = 8
        validator.validation_errors = 1
        
        stats = validator.get_performance_stats()
        
        assert stats['total_validations'] == 10
        assert stats['successful_validations'] == 8
        assert stats['validation_errors'] == 1
        assert stats['success_rate'] == 0.8
        assert stats['error_rate'] == 0.1
        assert 'validation_level' in stats
        assert 'forge_enabled' in stats
    
    @pytest.mark.asyncio
    async def test_cleanup(self, validator):
        """Test validation engine cleanup."""
        await validator.cleanup()
    
    def test_prepare_code_for_forge(self, validator):
        """Test code preparation for Forge compilation."""
        code_without_pragma = """
contract Test {
    function test() external {}
}
"""
        
        prepared = validator._prepare_code_for_forge(code_without_pragma)
        
        assert 'pragma solidity' in prepared
        assert 'contract Test' in prepared
    
    def test_security_rules_loading(self, validator):
        """Test security rules are properly loaded."""
        rules = validator.security_rules
        
        assert 'reentrancy' in rules
        assert 'tx_origin' in rules
        assert 'unchecked_call' in rules
        assert 'delegatecall' in rules
        
        for rule_name, rule_config in rules.items():
            assert 'pattern' in rule_config
            assert 'level' in rule_config
            assert 'message' in rule_config
            assert 'suggestion' in rule_config
