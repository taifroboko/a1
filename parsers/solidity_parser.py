"""
Solidity Parser - A1 Agentic System

Constrained Output Format parser that extracts Solidity code blocks from agent responses.
Implements regex-based parsing to extract exploit code delimited by triple quotes.

Based on the A1 research paper specifications.
"""

import re
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import time

logger = logging.getLogger(__name__)

class CodeBlockType(Enum):
    """Types of code blocks that can be parsed"""
    SOLIDITY = "solidity"
    VYPER = "vyper"
    JAVASCRIPT = "javascript"
    PYTHON = "python"
    UNKNOWN = "unknown"

@dataclass
class CodeBlock:
    """Parsed code block"""
    content: str
    block_type: CodeBlockType
    language: str
    start_position: int
    end_position: int
    line_start: int
    line_end: int
    metadata: Dict[str, Any]
    hash: str

@dataclass
class ParseResult:
    """Result of parsing operation"""
    success: bool
    code_blocks: List[CodeBlock]
    total_blocks: int
    solidity_blocks: int
    error_message: Optional[str]
    warnings: List[str]
    parsing_time: float
    original_text: str

class SolidityParser:
    """
    Advanced Solidity code parser for constrained output format.
    
    Extracts Solidity code blocks from agent responses using regex patterns
    and validates the structure for Forge testing compatibility.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the Solidity parser.
        
        Args:
            config: Configuration dictionary with parser settings
        """
        self.config = config or {}
        
        self.strict_mode = self.config.get('STRICT_PARSING', True)
        self.validate_syntax = self.config.get('VALIDATE_SYNTAX', True)
        self.extract_metadata = self.config.get('EXTRACT_METADATA', True)
        self.max_block_size = self.config.get('MAX_BLOCK_SIZE', 50000)  # 50KB max
        
        self.patterns = self._compile_patterns()
        
        self.total_parsed = 0
        self.successful_extractions = 0
        self.parsing_errors = 0
        
        self.parse_cache: Dict[str, ParseResult] = {}
        self.cache_max_size = self.config.get('CACHE_MAX_SIZE', 1000)
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for code block extraction."""
        patterns = {}
        
        patterns['triple_quotes'] = re.compile(
            r'```(?:solidity|sol)?\s*\n(.*?)\n```|'
            r"'''(?:solidity|sol)?\s*\n(.*?)\n'''",
            re.DOTALL | re.MULTILINE | re.IGNORECASE
        )
        
        patterns['explicit_markers'] = re.compile(
            r'//\s*SOLIDITY\s+START\s*\n(.*?)\n//\s*SOLIDITY\s+END',
            re.DOTALL | re.MULTILINE | re.IGNORECASE
        )
        
        patterns['pragma_blocks'] = re.compile(
            r'(pragma\s+solidity\s+[^;]+;.*?)(?=pragma\s+solidity|$)',
            re.DOTALL | re.MULTILINE | re.IGNORECASE
        )
        
        patterns['contract_blocks'] = re.compile(
            r'((?:abstract\s+)?(?:contract|interface|library)\s+\w+(?:\s+is\s+[^{]+)?\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
            re.DOTALL | re.MULTILINE
        )
        
        patterns['function_blocks'] = re.compile(
            r'(function\s+\w+\s*\([^)]*\)(?:\s+(?:public|private|internal|external|pure|view|payable|override|virtual|modifier)+)*\s*(?:returns\s*\([^)]*\))?\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
            re.DOTALL | re.MULTILINE
        )
        
        patterns['import_statements'] = re.compile(
            r'import\s+(?:"[^"]+"|\'[^\']+\'|\{[^}]+\}\s+from\s+(?:"[^"]+"|\'[^\']+\')|\w+(?:\s+as\s+\w+)?)\s*;',
            re.MULTILINE
        )
        
        return patterns
    
    def parse(self, text: str, use_cache: bool = True) -> ParseResult:
        """
        Parse text to extract Solidity code blocks.
        
        Args:
            text: Input text to parse
            use_cache: Whether to use cached results
            
        Returns:
            Parse result with extracted code blocks
        """
        start_time = time.time()
        
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        if use_cache and text_hash in self.parse_cache:
            cached_result = self.parse_cache[text_hash]
            logger.debug(f"Using cached parse result for text hash {text_hash[:8]}")
            return cached_result
        
        try:
            result = ParseResult(
                success=False,
                code_blocks=[],
                total_blocks=0,
                solidity_blocks=0,
                error_message=None,
                warnings=[],
                parsing_time=0.0,
                original_text=text
            )
            
            all_blocks = []
            
            triple_quote_blocks = self._extract_triple_quote_blocks(text)
            all_blocks.extend(triple_quote_blocks)
            
            marker_blocks = self._extract_marker_blocks(text)
            all_blocks.extend(marker_blocks)
            
            if not all_blocks:
                pragma_blocks = self._extract_pragma_blocks(text)
                all_blocks.extend(pragma_blocks)
            
            if not all_blocks:
                contract_blocks = self._extract_contract_blocks(text)
                all_blocks.extend(contract_blocks)
            
            unique_blocks = self._deduplicate_blocks(all_blocks)
            
            validated_blocks = []
            for block in unique_blocks:
                if self._validate_block(block):
                    enriched_block = self._enrich_block(block, text)
                    validated_blocks.append(enriched_block)
                else:
                    result.warnings.append(f"Invalid block at position {block.start_position}")
            
            result.code_blocks = validated_blocks
            result.total_blocks = len(validated_blocks)
            result.solidity_blocks = sum(1 for b in validated_blocks if b.block_type == CodeBlockType.SOLIDITY)
            result.success = result.solidity_blocks > 0
            result.parsing_time = time.time() - start_time
            
            if use_cache and len(self.parse_cache) < self.cache_max_size:
                self.parse_cache[text_hash] = result
            
            self.total_parsed += 1
            if result.success:
                self.successful_extractions += 1
            
            logger.info(f"Parsed {result.total_blocks} blocks ({result.solidity_blocks} Solidity) in {result.parsing_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.parsing_errors += 1
            error_msg = f"Parsing failed: {str(e)}"
            logger.error(error_msg)
            
            return ParseResult(
                success=False,
                code_blocks=[],
                total_blocks=0,
                solidity_blocks=0,
                error_message=error_msg,
                warnings=[],
                parsing_time=time.time() - start_time,
                original_text=text
            )
    
    def _extract_triple_quote_blocks(self, text: str) -> List[CodeBlock]:
        """Extract code blocks delimited by triple quotes."""
        blocks = []
        pattern = self.patterns['triple_quotes']
        
        for match in pattern.finditer(text):
            content = match.group(1) if match.group(1) else match.group(2)
            if not content:
                continue
            
            content = content.strip()
            if not content:
                continue
            
            full_match = match.group(0)
            language = self._detect_language_from_marker(full_match)
            
            block = CodeBlock(
                content=content,
                block_type=self._determine_block_type(content, language),
                language=language,
                start_position=match.start(),
                end_position=match.end(),
                line_start=text[:match.start()].count('\n') + 1,
                line_end=text[:match.end()].count('\n') + 1,
                metadata={'extraction_method': 'triple_quotes'},
                hash=hashlib.sha256(content.encode()).hexdigest()[:16]
            )
            
            blocks.append(block)
        
        return blocks
    
    def _extract_marker_blocks(self, text: str) -> List[CodeBlock]:
        """Extract code blocks with explicit markers."""
        blocks = []
        pattern = self.patterns['explicit_markers']
        
        for match in pattern.finditer(text):
            content = match.group(1).strip()
            if not content:
                continue
            
            block = CodeBlock(
                content=content,
                block_type=CodeBlockType.SOLIDITY,
                language='solidity',
                start_position=match.start(),
                end_position=match.end(),
                line_start=text[:match.start()].count('\n') + 1,
                line_end=text[:match.end()].count('\n') + 1,
                metadata={'extraction_method': 'explicit_markers'},
                hash=hashlib.sha256(content.encode()).hexdigest()[:16]
            )
            
            blocks.append(block)
        
        return blocks
    
    def _extract_pragma_blocks(self, text: str) -> List[CodeBlock]:
        """Extract code blocks starting with pragma statements."""
        blocks = []
        pattern = self.patterns['pragma_blocks']
        
        for match in pattern.finditer(text):
            content = match.group(1).strip()
            if not content:
                continue
            
            block = CodeBlock(
                content=content,
                block_type=CodeBlockType.SOLIDITY,
                language='solidity',
                start_position=match.start(),
                end_position=match.end(),
                line_start=text[:match.start()].count('\n') + 1,
                line_end=text[:match.end()].count('\n') + 1,
                metadata={'extraction_method': 'pragma_detection'},
                hash=hashlib.sha256(content.encode()).hexdigest()[:16]
            )
            
            blocks.append(block)
        
        return blocks
    
    def _extract_contract_blocks(self, text: str) -> List[CodeBlock]:
        """Extract complete contract definitions."""
        blocks = []
        pattern = self.patterns['contract_blocks']
        
        for match in pattern.finditer(text):
            content = match.group(1).strip()
            if not content:
                continue
            
            block = CodeBlock(
                content=content,
                block_type=CodeBlockType.SOLIDITY,
                language='solidity',
                start_position=match.start(),
                end_position=match.end(),
                line_start=text[:match.start()].count('\n') + 1,
                line_end=text[:match.end()].count('\n') + 1,
                metadata={'extraction_method': 'contract_detection'},
                hash=hashlib.sha256(content.encode()).hexdigest()[:16]
            )
            
            blocks.append(block)
        
        return blocks
    
    def _detect_language_from_marker(self, marker_text: str) -> str:
        """Detect programming language from code block marker."""
        marker_lower = marker_text.lower()
        
        if 'solidity' in marker_lower or 'sol' in marker_lower:
            return 'solidity'
        elif 'vyper' in marker_lower or 'vy' in marker_lower:
            return 'vyper'
        elif 'javascript' in marker_lower or 'js' in marker_lower:
            return 'javascript'
        elif 'python' in marker_lower or 'py' in marker_lower:
            return 'python'
        else:
            return 'unknown'
    
    def _determine_block_type(self, content: str, language: str) -> CodeBlockType:
        """Determine the type of code block based on content and language."""
        if language == 'solidity':
            return CodeBlockType.SOLIDITY
        elif language == 'vyper':
            return CodeBlockType.VYPER
        elif language == 'javascript':
            return CodeBlockType.JAVASCRIPT
        elif language == 'python':
            return CodeBlockType.PYTHON
        
        content_lower = content.lower()
        
        solidity_keywords = ['pragma solidity', 'contract ', 'interface ', 'library ', 
                           'function ', 'modifier ', 'event ', 'struct ', 'enum ',
                           'mapping(', 'address', 'uint256', 'bytes32']
        
        if any(keyword in content_lower for keyword in solidity_keywords):
            return CodeBlockType.SOLIDITY
        
        vyper_keywords = ['@external', '@internal', '@pure', '@view', 'def ', 'struct ']
        if any(keyword in content_lower for keyword in vyper_keywords):
            return CodeBlockType.VYPER
        
        return CodeBlockType.UNKNOWN
    
    def _deduplicate_blocks(self, blocks: List[CodeBlock]) -> List[CodeBlock]:
        """Remove duplicate and overlapping code blocks."""
        if not blocks:
            return blocks
        
        sorted_blocks = sorted(blocks, key=lambda b: b.start_position)
        
        seen_hashes = set()
        unique_blocks = []
        
        for block in sorted_blocks:
            if block.hash not in seen_hashes:
                seen_hashes.add(block.hash)
                unique_blocks.append(block)
        
        final_blocks = []
        for i, block in enumerate(unique_blocks):
            is_overlapped = False
            
            for j, other_block in enumerate(unique_blocks):
                if i != j:
                    if (block.start_position < other_block.end_position and 
                        block.end_position > other_block.start_position):
                        if len(block.content) < len(other_block.content):
                            is_overlapped = True
                            break
            
            if not is_overlapped:
                final_blocks.append(block)
        
        return final_blocks
    
    def _validate_block(self, block: CodeBlock) -> bool:
        """Validate a code block."""
        if len(block.content) > self.max_block_size:
            logger.warning(f"Block exceeds size limit: {len(block.content)} > {self.max_block_size}")
            return False
        
        if len(block.content.strip()) < 10:
            return False
        
        if block.block_type == CodeBlockType.SOLIDITY:
            return self._validate_solidity_block(block)
        
        return True
    
    def _validate_solidity_block(self, block: CodeBlock) -> bool:
        """Validate Solidity-specific syntax and structure."""
        content = block.content.strip()
        
        has_pragma = 'pragma solidity' in content.lower()
        has_contract = any(keyword in content.lower() for keyword in ['contract ', 'interface ', 'library '])
        has_function = 'function ' in content.lower()
        
        if not (has_pragma or has_contract or has_function):
            return False
        
        if not self._check_balanced_braces(content):
            return False
        
        if self.validate_syntax:
            return self._validate_solidity_syntax(content)
        
        return True
    
    def _check_balanced_braces(self, content: str) -> bool:
        """Check if braces are balanced in the code."""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        for char in content:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs[stack.pop()] != char:
                    return False
        
        return len(stack) == 0
    
    def _validate_solidity_syntax(self, content: str) -> bool:
        """Perform basic Solidity syntax validation."""
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            if line.endswith('{') or line.endswith('}') or line.endswith(';'):
                continue
            
            if line.strip().startswith('function '):
                if not (line.endswith('{') or line.endswith(';')):
                    logger.debug(f"Potential syntax error at line {line_num}: {line}")
                    return False
        
        return True
    
    def _enrich_block(self, block: CodeBlock, original_text: str) -> CodeBlock:
        """Enrich code block with additional metadata."""
        if not self.extract_metadata:
            return block
        
        metadata = block.metadata.copy()
        
        imports = self._extract_imports(block.content)
        if imports:
            metadata['imports'] = imports
        
        contracts = self._extract_contract_names(block.content)
        if contracts:
            metadata['contracts'] = contracts
        
        functions = self._extract_function_names(block.content)
        if functions:
            metadata['functions'] = functions
        
        metadata['complexity'] = self._calculate_complexity(block.content)
        
        comments = self._extract_comments(block.content)
        if comments:
            metadata['comments'] = comments
        
        return CodeBlock(
            content=block.content,
            block_type=block.block_type,
            language=block.language,
            start_position=block.start_position,
            end_position=block.end_position,
            line_start=block.line_start,
            line_end=block.line_end,
            metadata=metadata,
            hash=block.hash
        )
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from code."""
        imports = []
        pattern = self.patterns['import_statements']
        
        for match in pattern.finditer(content):
            imports.append(match.group(0).strip())
        
        return imports
    
    def _extract_contract_names(self, content: str) -> List[str]:
        """Extract contract names from code."""
        contracts = []
        pattern = re.compile(r'(?:contract|interface|library)\s+(\w+)', re.IGNORECASE)
        
        for match in pattern.finditer(content):
            contracts.append(match.group(1))
        
        return contracts
    
    def _extract_function_names(self, content: str) -> List[str]:
        """Extract function names from code."""
        functions = []
        pattern = re.compile(r'function\s+(\w+)', re.IGNORECASE)
        
        for match in pattern.finditer(content):
            functions.append(match.group(1))
        
        return functions
    
    def _calculate_complexity(self, content: str) -> Dict[str, int]:
        """Calculate basic complexity metrics."""
        return {
            'lines': len(content.split('\n')),
            'characters': len(content),
            'functions': len(re.findall(r'function\s+\w+', content, re.IGNORECASE)),
            'contracts': len(re.findall(r'(?:contract|interface|library)\s+\w+', content, re.IGNORECASE)),
            'statements': content.count(';'),
            'braces': content.count('{')
        }
    
    def _extract_comments(self, content: str) -> List[str]:
        """Extract comments from code."""
        comments = []
        
        single_line_pattern = re.compile(r'//.*$', re.MULTILINE)
        comments.extend([match.group(0).strip() for match in single_line_pattern.finditer(content)])
        
        multi_line_pattern = re.compile(r'/\*.*?\*/', re.DOTALL)
        comments.extend([match.group(0).strip() for match in multi_line_pattern.finditer(content)])
        
        return comments
    
    def extract_solidity_blocks(self, text: str) -> List[CodeBlock]:
        """
        Extract only Solidity code blocks from text.
        
        Args:
            text: Input text to parse
            
        Returns:
            List of Solidity code blocks
        """
        result = self.parse(text)
        return [block for block in result.code_blocks if block.block_type == CodeBlockType.SOLIDITY]
    
    def get_largest_block(self, text: str) -> Optional[CodeBlock]:
        """Get the largest code block from text."""
        result = self.parse(text)
        if not result.code_blocks:
            return None
        
        return max(result.code_blocks, key=lambda b: len(b.content))
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get parser performance statistics."""
        return {
            'total_parsed': self.total_parsed,
            'successful_extractions': self.successful_extractions,
            'parsing_errors': self.parsing_errors,
            'success_rate': self.successful_extractions / max(self.total_parsed, 1),
            'cache_size': len(self.parse_cache),
            'cache_hit_rate': 0.0  # Would need to track cache hits
        }
    
    def clear_cache(self):
        """Clear the parsing cache."""
        self.parse_cache.clear()
        logger.info("Parser cache cleared")
    
    def validate_extracted_code(self, code_blocks: List[CodeBlock]) -> Dict[str, Any]:
        """
        Validate extracted code blocks for Forge compatibility.
        
        Args:
            code_blocks: List of code blocks to validate
            
        Returns:
            Validation results
        """
        validation_results = {
            'total_blocks': len(code_blocks),
            'valid_blocks': 0,
            'invalid_blocks': 0,
            'warnings': [],
            'errors': [],
            'forge_compatible': 0
        }
        
        for i, block in enumerate(code_blocks):
            block_valid = True
            
            if block.block_type != CodeBlockType.SOLIDITY:
                validation_results['warnings'].append(f"Block {i}: Not a Solidity block")
                continue
            
            content = block.content.lower()
            
            if not ('pragma solidity' in content or 
                   any(keyword in content for keyword in ['contract ', 'interface ', 'library '])):
                validation_results['errors'].append(f"Block {i}: Missing pragma or contract definition")
                block_valid = False
            
            if 'test' in content:
                if not ('function test' in content or 'contract test' in content):
                    validation_results['warnings'].append(f"Block {i}: Appears to be test but missing test functions")
            
            if block_valid:
                validation_results['valid_blocks'] += 1
                
                if self._is_forge_compatible(block):
                    validation_results['forge_compatible'] += 1
            else:
                validation_results['invalid_blocks'] += 1
        
        return validation_results
    
    def _is_forge_compatible(self, block: CodeBlock) -> bool:
        """Check if a code block is compatible with Forge testing."""
        content = block.content.lower()
        
        forge_indicators = [
            'pragma solidity',
            'import "forge-std/',
            'import {test}',
            'contract test',
            'function test',
            'function setup()',
            'asserteq(',
            'asserttrue(',
            'assertfalse('
        ]
        
        return any(indicator in content for indicator in forge_indicators)
