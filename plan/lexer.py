import re
from typing import List, NamedTuple, Optional
from common.diagnostics import CompileError

class Token(NamedTuple):
    type: str
    value: str
    line: int
    column: int
    
class Lexer:
    """PLAN Lexer: Breaks English-like text into tokens."""
    
    # Token specification
    RULES = [
        ('PYTHON_BLOCK', r'[Pp][Yy][Tt][Hh][Oo][Nn]:\s*(?:\r?\n[ \t]+.*)+'), # python: followed by indented lines
        ('COMMENT',  r'[Nn][Oo][Tt][Ee]:.*'),           # Comment line
        ('STRING',   r'"[^"]*"'),               # String literal
        ('NUMBER',   r'\d+(\.\d*)?'),           # Integer or decimal number
        ('IDENT',    r'[A-Za-z_][A-Za-z0-9_]*'),# Identifiers and keywords
        ('COMMA',    r','),                     # Comma separator
        ('PERIOD',   r'\.'),                    # End of sentence
        ('OP',       r'[+\-*/=<>]'),            # Math/Comparison operators
        ('WS',       r'\s+'),                   # Whitespace (ignored)
        ('MISMATCH', r'.'),                     # Any other character
    ]
    
    TOK_REGEX = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in RULES))
    
    KEYWORDS = {
        'create', 'a', 'variable', 'called', 'with', 'value',
        'when', 'is', 'greater', 'than', 'or', 'equal', 'to',
        'show', 'otherwise', 'and', 'not', 'less', 'set',
        'add', 'subtract', 'multiply', 'divide', 'loop', 'times',
        'function', 'that', 'takes', 'returns', 'return', 'end'
    }

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tokens: List[Token] = []
        
    def tokenize(self) -> List[Token]:
        line_num = 1
        line_start = 0
        
        for mo in self.TOK_REGEX.finditer(self.source_code):
            kind = mo.lastgroup
            value = mo.group(kind)
            column = mo.start() - line_start + 1
            
            if kind == 'WS' or kind == 'COMMENT':
                if '\n' in value:
                    line_num += value.count('\n')
                    # Find the last newline in the matched whitespace to reset line_start
                    last_newline_pos = value.rfind('\n')
                    line_start = mo.start() + last_newline_pos + 1
                continue
            
            if kind == 'MISMATCH':
                raise CompileError(
                    f"Unexpected character '{value}'",
                    line=line_num,
                    column=column,
                    source_line=self._get_line(line_num)
                )
                
            if kind == 'IDENT':
                # Keywords are case-insensitive
                lower_val = value.lower()
                if lower_val in self.KEYWORDS:
                    kind = 'KEYWORD'
                    value = lower_val # Normalize keywords to lowercase
                elif lower_val in {'true', 'false'}:
                    kind = 'BOOLEAN'
                    value = lower_val
                    
            if kind == 'STRING':
                value = value[1:-1] # Strip quotes
                
            self.tokens.append(Token(kind, value, line_num, column))
            
        self.tokens.append(Token('EOF', '', line_num, column + 1))
        return self.tokens

    def _get_line(self, line_num: int) -> str:
        lines = self.source_code.split('\n')
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1]
        return ""
