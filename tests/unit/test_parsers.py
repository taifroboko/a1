"""
Unit Tests - Solidity Parser

Test the constrained output format parser for extracting Solidity code blocks.
"""

import pytest
from parsers.solidity_parser import SolidityParser, CodeBlock, CodeBlockType, ParseResult

class TestSolidityParser:
    """Test cases for SolidityParser."""
    
    @pytest.fixture
    def parser(self, test_config):
        """Create parser instance."""
        return SolidityParser(test_config)
    
    def test_parse_triple_quotes_solidity(self, parser):
        """Test parsing Solidity code in triple quotes."""
        text = """
Here's the exploit code:

```solidity
pragma solidity ^0.8.0;

contract TestExploit {
    function exploit() external payable {
        // Exploit logic here
    }
}
```

This should work.
"""
        
        result = parser.parse(text)
        
        assert result.success
        assert result.solidity_blocks == 1
        assert len(result.code_blocks) == 1
        
        block = result.code_blocks[0]
        assert block.block_type == CodeBlockType.SOLIDITY
        assert 'pragma solidity' in block.content
        assert 'contract TestExploit' in block.content
        assert 'function exploit' in block.content
    
    def test_parse_multiple_blocks(self, parser):
        """Test parsing multiple code blocks."""
        text = """
First contract:
```solidity
contract First {
    function test1() external {}
}
```

Second contract:
```sol
contract Second {
    function test2() external {}
}
```
"""
        
        result = parser.parse(text)
        
        assert result.success
        assert result.solidity_blocks == 2
        assert len(result.code_blocks) == 2
        
        assert 'contract First' in result.code_blocks[0].content
        assert 'contract Second' in result.code_blocks[1].content
    
    def test_parse_explicit_markers(self, parser):
        """Test parsing with explicit markers."""
        text = """
// SOLIDITY START
pragma solidity ^0.8.0;

contract MarkerTest {
    function test() external {}
}
// SOLIDITY END
"""
        
        result = parser.parse(text)
        
        assert result.success
        assert result.solidity_blocks == 1
        assert 'contract MarkerTest' in result.code_blocks[0].content
    
    def test_parse_pragma_detection(self, parser):
        """Test pragma-based detection."""
        text = """
pragma solidity ^0.8.0;

contract PragmaTest {
    function test() external {}
}

pragma solidity ^0.7.0;

contract AnotherContract {
    function test2() external {}
}
"""
        
        result = parser.parse(text)
        
        assert result.success
        assert result.solidity_blocks >= 1
    
    def test_parse_contract_detection(self, parser):
        """Test contract-based detection."""
        text = """
contract ContractTest {
    mapping(address => uint256) public balances;
    
    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }
}
"""
        
        result = parser.parse(text)
        
        assert result.success
        assert result.solidity_blocks == 1
        assert 'contract ContractTest' in result.code_blocks[0].content
    
    def test_parse_no_solidity_code(self, parser):
        """Test parsing text with no Solidity code."""
        text = """
This is just regular text with no code blocks.
Maybe some JavaScript:

```javascript
console.log("Hello world");
```

But no Solidity.
"""
        
        result = parser.parse(text)
        
        assert not result.success
        assert result.solidity_blocks == 0
    
    def test_parse_invalid_solidity(self, parser):
        """Test parsing invalid Solidity code."""
        text = """
```solidity
this is not valid solidity code
missing semicolons and braces
```
"""
        
        result = parser.parse(text)
        
        assert len(result.code_blocks) == 1
        assert result.code_blocks[0].block_type == CodeBlockType.SOLIDITY
    
    def test_extract_solidity_blocks_only(self, parser):
        """Test extracting only Solidity blocks."""
        text = """
```python
print("This is Python")
```

```solidity
contract Test {
    function test() external {}
}
```

```javascript
console.log("This is JavaScript");
```
"""
        
        solidity_blocks = parser.extract_solidity_blocks(text)
        
        assert len(solidity_blocks) == 1
        assert solidity_blocks[0].block_type == CodeBlockType.SOLIDITY
        assert 'contract Test' in solidity_blocks[0].content
    
    def test_get_largest_block(self, parser):
        """Test getting the largest code block."""
        text = """
```solidity
contract Small {}
```

```solidity
contract Large {
    mapping(address => uint256) public balances;
    
    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }
    
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }
}
```
"""
        
        largest = parser.get_largest_block(text)
        
        assert largest is not None
        assert 'contract Large' in largest.content
        assert len(largest.content) > 50
    
    def test_validate_extracted_code(self, parser):
        """Test validation of extracted code blocks."""
        text = """
```solidity
pragma solidity ^0.8.0;

contract ValidContract {
    function test() external {}
}
```

```solidity
invalid solidity code here
```
"""
        
        result = parser.parse(text)
        validation_results = parser.validate_extracted_code(result.code_blocks)
        
        assert validation_results['total_blocks'] == 2
        assert validation_results['valid_blocks'] >= 1
        assert validation_results['invalid_blocks'] >= 0
    
    def test_performance_stats(self, parser):
        """Test parser performance statistics."""
        parser.parse("```solidity\ncontract Test {}\n```")
        parser.parse("No code here")
        
        stats = parser.get_performance_stats()
        
        assert 'total_parsed' in stats
        assert 'successful_extractions' in stats
        assert 'parsing_errors' in stats
        assert 'success_rate' in stats
        assert stats['total_parsed'] >= 2
    
    def test_cache_functionality(self, parser):
        """Test parsing cache functionality."""
        text = "```solidity\ncontract Test {}\n```"
        
        result1 = parser.parse(text, use_cache=True)
        
        result2 = parser.parse(text, use_cache=True)
        
        assert result1.success == result2.success
        assert len(result1.code_blocks) == len(result2.code_blocks)
        
        parser.clear_cache()
        stats = parser.get_performance_stats()
        assert stats['cache_size'] == 0
