"""
Code Sanitizer Tool - A1 Agentic System

This tool removes comments, unused code, and extraneous library dependencies,
enabling the agent to focus its analysis exclusively on executable logic
without the dangers of potentially misleading documentation.

Based on the A1 research paper specifications.
"""

import re
import ast
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SanitizedCode:
    """Container for sanitized code information"""
    original_code: str
    sanitized_code: str
    removed_comments: List[str]
    removed_imports: List[str]
    removed_functions: List[str]
    optimization_summary: Dict[str, int]

class CodeSanitizer:
    """
    Sanitizes smart contract source code for focused analysis.
    
    Removes non-essential elements including comments, unused code,
    and extraneous library dependencies to enable focused analysis
    on executable logic only.
    """
    
    def __init__(self):
        """Initialize the code sanitizer."""
        
        self.COMMENT_PATTERNS = {
            'single_line': r'//.*?$',
            'multi_line': r'/\*.*?\*/',
            'natspec_single': r'///.*?$',
            'natspec_multi': r'/\*\*.*?\*/',
            'pragma_comments': r'//\s*SPDX-License-Identifier:.*?$'
        }
        
        self.COMMON_UNUSED_IMPORTS = {
            'SafeMath',
            'Address',
            'Strings',
            'Counters',
            'EnumerableSet',
            'EnumerableMap',
            'ReentrancyGuard',
            'Pausable'
        }
        
        self.DEAD_CODE_PATTERNS = {
            'unreachable_after_return': r'return\s+[^;]+;\s*\n\s*[^}]',
            'unreachable_after_revert': r'revert\([^)]*\);\s*\n\s*[^}]',
            'unreachable_after_require_false': r'require\(false[^)]*\);\s*\n\s*[^}]',
            'empty_functions': r'function\s+\w+\([^)]*\)\s*(?:public|private|internal|external)?\s*(?:view|pure)?\s*(?:returns\s*\([^)]*\))?\s*\{\s*\}',
            'unused_modifiers': r'modifier\s+\w+\([^)]*\)\s*\{[^}]*\}'
        }
    
    def sanitize_contract_code(self, source_code: str, contract_name: Optional[str] = None) -> SanitizedCode:
        """
        Sanitize smart contract source code.
        
        Args:
            source_code: Raw contract source code
            contract_name: Name of the main contract to focus on
            
        Returns:
            SanitizedCode object with cleaned code and removal summary
        """
        logger.info(f"Sanitizing contract code for: {contract_name or 'unknown'}")
        
        original_code = source_code
        sanitized_code = source_code
        removed_comments = []
        removed_imports = []
        removed_functions = []
        
        sanitized_code, comments = self._remove_comments(sanitized_code)
        removed_comments.extend(comments)
        
        sanitized_code, imports = self._remove_unused_imports(sanitized_code)
        removed_imports.extend(imports)
        
        sanitized_code, functions = self._remove_dead_code(sanitized_code)
        removed_functions.extend(functions)
        
        if contract_name:
            sanitized_code = self._focus_on_main_contract(sanitized_code, contract_name)
        
        sanitized_code = self._clean_whitespace(sanitized_code)
        
        optimization_summary = {
            'original_lines': len(original_code.split('\n')),
            'sanitized_lines': len(sanitized_code.split('\n')),
            'removed_comments': len(removed_comments),
            'removed_imports': len(removed_imports),
            'removed_functions': len(removed_functions),
            'size_reduction_percent': round((1 - len(sanitized_code) / max(len(original_code), 1)) * 100, 2)
        }
        
        return SanitizedCode(
            original_code=original_code,
            sanitized_code=sanitized_code,
            removed_comments=removed_comments,
            removed_imports=removed_imports,
            removed_functions=removed_functions,
            optimization_summary=optimization_summary
        )
    
    def _remove_comments(self, code: str) -> Tuple[str, List[str]]:
        """Remove all types of comments from the code."""
        removed_comments = []
        
        def replace_multiline_comment(match):
            comment = match.group(0)
            removed_comments.append(comment.strip())
            return '\n' * comment.count('\n')
        
        code = re.sub(self.COMMENT_PATTERNS['natspec_multi'], replace_multiline_comment, code, flags=re.DOTALL)
        
        code = re.sub(self.COMMENT_PATTERNS['multi_line'], replace_multiline_comment, code, flags=re.DOTALL)
        
        def replace_single_comment(match):
            comment = match.group(0)
            removed_comments.append(comment.strip())
            return ''
        
        code = re.sub(self.COMMENT_PATTERNS['natspec_single'], replace_single_comment, code, flags=re.MULTILINE)
        
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            comment_match = re.search(r'//', line)
            if comment_match:
                if 'SPDX-License-Identifier' in line:
                    cleaned_lines.append(line)
                else:
                    before_comment = line[:comment_match.start()].rstrip()
                    comment_part = line[comment_match.start():].strip()
                    if comment_part:
                        removed_comments.append(comment_part)
                    cleaned_lines.append(before_comment)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines), removed_comments
    
    def _remove_unused_imports(self, code: str) -> Tuple[str, List[str]]:
        """Remove unused import statements."""
        removed_imports = []
        lines = code.split('\n')
        cleaned_lines = []
        
        import_pattern = r'import\s+(?:"[^"]+"|{[^}]+}|\w+)\s+from\s+"[^"]+";?'
        using_pattern = r'using\s+\w+\s+for\s+[^;]+;'
        
        for line in lines:
            line_stripped = line.strip()
            
            if re.match(import_pattern, line_stripped) or re.match(using_pattern, line_stripped):
                imported_item = self._extract_imported_item(line_stripped)
                
                if imported_item and self._is_import_unused(imported_item, code):
                    removed_imports.append(line_stripped)
                    continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines), removed_imports
    
    def _extract_imported_item(self, import_line: str) -> Optional[str]:
        """Extract the main imported item from an import statement."""
        
        simple_import = re.search(r'import\s+"[^"]*?/(\w+)\.sol"', import_line)
        if simple_import:
            return simple_import.group(1)
        
        named_import = re.search(r'import\s+\{([^}]+)\}', import_line)
        if named_import:
            items = named_import.group(1).split(',')
            return items[0].strip()
        
        default_import = re.search(r'import\s+(\w+)\s+from', import_line)
        if default_import:
            return default_import.group(1)
        
        using_import = re.search(r'using\s+(\w+)\s+for', import_line)
        if using_import:
            return using_import.group(1)
        
        return None
    
    def _is_import_unused(self, imported_item: str, code: str) -> bool:
        """Check if an imported item is actually used in the code."""
        code_without_imports = re.sub(r'import[^;]+;', '', code)
        code_without_imports = re.sub(r'using[^;]+;', '', code_without_imports)
        
        usage_pattern = r'\b' + re.escape(imported_item) + r'\b'
        
        if re.search(usage_pattern, code_without_imports):
            return False  # Item is used
        
        if imported_item in self.COMMON_UNUSED_IMPORTS:
            return True  # Likely unused
        
        return False  # Keep if uncertain
    
    def _remove_dead_code(self, code: str) -> Tuple[str, List[str]]:
        """Remove dead and unreachable code."""
        removed_functions = []
        
        def replace_empty_function(match):
            function_def = match.group(0)
            removed_functions.append(f"Empty function: {function_def[:50]}...")
            return ''
        
        code = re.sub(self.DEAD_CODE_PATTERNS['empty_functions'], replace_empty_function, code, flags=re.DOTALL)
        
        code = self._remove_unreachable_code(code)
        
        code = self._remove_unused_modifiers(code, removed_functions)
        
        return code, removed_functions
    
    def _remove_unreachable_code(self, code: str) -> str:
        """Remove code that appears after return/revert statements."""
        lines = code.split('\n')
        cleaned_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            cleaned_lines.append(line)
            
            if re.search(r'\b(return|revert)\b', line.strip()) and line.strip().endswith(';'):
                j = i + 1
                brace_count = 0
                
                while j < len(lines):
                    next_line = lines[j].strip()
                    
                    brace_count += next_line.count('{') - next_line.count('}')
                    
                    if brace_count < 0:
                        cleaned_lines.append(lines[j])
                        break
                    
                    if re.search(r'\b(function|modifier|constructor)\b', next_line):
                        cleaned_lines.append(lines[j])
                        break
                    
                    j += 1
                
                i = j
            else:
                i += 1
        
        return '\n'.join(cleaned_lines)
    
    def _remove_unused_modifiers(self, code: str, removed_functions: List[str]) -> str:
        """Remove modifiers that are never used."""
        modifier_pattern = r'modifier\s+(\w+)\s*\([^)]*\)\s*\{[^}]*\}'
        modifiers = re.findall(r'modifier\s+(\w+)', code)
        
        for modifier_name in modifiers:
            usage_pattern = r'\b' + re.escape(modifier_name) + r'\b'
            
            occurrences = len(re.findall(usage_pattern, code))
            
            if occurrences <= 1:  # Only the definition exists
                modifier_def_pattern = r'modifier\s+' + re.escape(modifier_name) + r'\s*\([^)]*\)\s*\{[^}]*\}'
                code = re.sub(modifier_def_pattern, '', code, flags=re.DOTALL)
                removed_functions.append(f"Unused modifier: {modifier_name}")
        
        return code
    
    def _focus_on_main_contract(self, code: str, contract_name: str) -> str:
        """Focus on the main contract and remove auxiliary contracts."""
        contract_pattern = r'contract\s+' + re.escape(contract_name) + r'\s*(?:is\s+[^{]+)?\s*\{.*?\n\}'
        
        match = re.search(contract_pattern, code, flags=re.DOTALL)
        if match:
            main_contract = match.group(0)
            
            pragmas = re.findall(r'pragma[^;]+;', code)
            imports = re.findall(r'import[^;]+;', code)
            licenses = re.findall(r'//\s*SPDX-License-Identifier:[^\n]+', code)
            
            essential_parts = []
            essential_parts.extend(licenses)
            essential_parts.extend(pragmas)
            essential_parts.extend(imports)
            essential_parts.append(main_contract)
            
            return '\n\n'.join(essential_parts)
        
        return code  # Return original if main contract not found
    
    def _clean_whitespace(self, code: str) -> str:
        """Clean up excessive whitespace while preserving readability."""
        lines = [line.rstrip() for line in code.split('\n')]
        
        cleaned_lines = []
        blank_count = 0
        
        for line in lines:
            if line.strip() == '':
                blank_count += 1
                if blank_count <= 2:
                    cleaned_lines.append(line)
            else:
                blank_count = 0
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def analyze_code_complexity(self, code: str) -> Dict[str, int]:
        """
        Analyze code complexity metrics.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Dictionary with complexity metrics
        """
        metrics = {
            'total_lines': len(code.split('\n')),
            'non_empty_lines': len([line for line in code.split('\n') if line.strip()]),
            'function_count': len(re.findall(r'\bfunction\s+\w+', code)),
            'modifier_count': len(re.findall(r'\bmodifier\s+\w+', code)),
            'event_count': len(re.findall(r'\bevent\s+\w+', code)),
            'state_variable_count': len(re.findall(r'^\s*(?:uint|int|bool|address|string|bytes|mapping)\s+(?:public|private|internal)?\s*\w+', code, re.MULTILINE)),
            'external_calls': len(re.findall(r'\.call\(|\.delegatecall\(|\.staticcall\(', code)),
            'require_statements': len(re.findall(r'\brequire\s*\(', code)),
            'assert_statements': len(re.findall(r'\bassert\s*\(', code)),
            'revert_statements': len(re.findall(r'\brevert\s*\(', code))
        }
        
        complexity_score = (
            metrics['function_count'] * 2 +
            metrics['modifier_count'] * 1 +
            metrics['state_variable_count'] * 1 +
            metrics['external_calls'] * 3 +
            metrics['require_statements'] * 0.5
        )
        
        metrics['complexity_score'] = complexity_score
        metrics['complexity_level'] = (
            'low' if complexity_score < 20 else
            'medium' if complexity_score < 50 else
            'high'
        )
        
        return metrics
    
    def extract_critical_functions(self, code: str) -> List[Dict[str, str]]:
        """
        Extract functions that are commonly targeted in exploits.
        
        Args:
            code: Source code to analyze
            
        Returns:
            List of critical function information
        """
        critical_functions = []
        
        critical_patterns = {
            'transfer_functions': r'function\s+(\w*transfer\w*)\s*\([^)]*\)',
            'approval_functions': r'function\s+(\w*approve\w*)\s*\([^)]*\)',
            'mint_functions': r'function\s+(\w*mint\w*)\s*\([^)]*\)',
            'burn_functions': r'function\s+(\w*burn\w*)\s*\([^)]*\)',
            'withdraw_functions': r'function\s+(\w*withdraw\w*)\s*\([^)]*\)',
            'deposit_functions': r'function\s+(\w*deposit\w*)\s*\([^)]*\)',
            'swap_functions': r'function\s+(\w*swap\w*)\s*\([^)]*\)',
            'admin_functions': r'function\s+(\w*(?:admin|owner|governance)\w*)\s*\([^)]*\)',
            'emergency_functions': r'function\s+(\w*(?:emergency|pause|stop)\w*)\s*\([^)]*\)'
        }
        
        for category, pattern in critical_patterns.items():
            matches = re.finditer(pattern, code, re.IGNORECASE)
            
            for match in matches:
                function_name = match.group(1)
                
                start_pos = match.start()
                brace_count = 0
                end_pos = start_pos
                
                for i, char in enumerate(code[start_pos:], start_pos):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                function_def = code[start_pos:end_pos]
                
                critical_functions.append({
                    'name': function_name,
                    'category': category,
                    'definition': function_def,
                    'visibility': self._extract_function_visibility(function_def),
                    'modifiers': self._extract_function_modifiers(function_def)
                })
        
        return critical_functions
    
    def _extract_function_visibility(self, function_def: str) -> str:
        """Extract function visibility from definition."""
        if 'public' in function_def:
            return 'public'
        elif 'external' in function_def:
            return 'external'
        elif 'internal' in function_def:
            return 'internal'
        elif 'private' in function_def:
            return 'private'
        else:
            return 'default'
    
    def _extract_function_modifiers(self, function_def: str) -> List[str]:
        """Extract modifiers applied to a function."""
        signature_end = function_def.find(')')
        brace_start = function_def.find('{')
        
        if signature_end != -1 and brace_start != -1:
            modifier_section = function_def[signature_end:brace_start]
            
            modifier_section = re.sub(r'\b(public|private|internal|external|view|pure|payable|nonpayable)\b', '', modifier_section)
            modifier_section = re.sub(r'\breturns\s*\([^)]*\)', '', modifier_section)
            
            modifiers = re.findall(r'\b\w+\b', modifier_section)
            return [mod for mod in modifiers if mod not in ['returns']]
        
        return []
