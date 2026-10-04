from typing import List, Optional
from plan.lexer import Token, Lexer
from plan.ast_nodes import *
from common.diagnostics import CompileError

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1] # EOF

    def next_token(self) -> Token:
        tok = self.peek()
        if tok.type != 'EOF':
            self.pos += 1
        return tok

    def consume(self, expected_type: str, expected_value: Optional[str] = None):
        tok = self.peek()
        if tok.type == expected_type and (expected_value is None or tok.value.lower() == expected_value.lower()):
            return self.next_token()
        
        expected_msg = expected_type
        if expected_value:
            expected_msg = f"'{expected_value}'"
            
        raise CompileError(
            f"Expected {expected_msg}, but got '{tok.value}'",
            line=tok.line, column=tok.column
        )
        
    def match(self, expected_type: str, expected_value: Optional[str] = None) -> bool:
        tok = self.peek()
        if tok.type == expected_type and (expected_value is None or tok.value.lower() == expected_value.lower()):
            self.pos += 1
            return True
        return False
        
    def match_keyword(self, kw: str) -> bool:
        return self.match('KEYWORD', kw)
        
    def parse_program(self) -> Program:
        statements = []
        while self.peek().type != 'EOF':
            statements.append(self.parse_sentence())
        return Program(line=1, column=1, statements=statements)
        
    def parse_sentence(self) -> Statement:
        # A simple statement ends with `.`
        # A block header ends with `,`
        # We look at the first keyword
        tok = self.peek()
        if tok.type == 'KEYWORD':
            val = tok.value.lower()
            if val == 'create':
                return self.parse_declare_or_function()
            elif val == 'let':
                return self.parse_let()
            elif val == 'set':
                return self.parse_set()
            elif val == 'show':
                return self.parse_show()
            # TODO: add all other statement types
            
        if tok.type == 'PYTHON_BLOCK':
            self.next_token()
            # Extract the raw code lines, stripping "python:"
            code = tok.value
            colon_idx = code.find(':')
            raw_code = code[colon_idx+1:].strip('\r\n')
            
            # De-indent the raw code
            lines = raw_code.split('\n')
            if lines:
                # Find minimum indentation of non-empty lines
                indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
                min_indent = min(indents) if indents else 0
                deindented_lines = [line[min_indent:] if len(line) >= min_indent else line for line in lines]
                raw_code = '\n'.join(deindented_lines)
                
            return PythonRaw(line=tok.line, column=tok.column, code=raw_code)
            
        # fallback
        raise CompileError(f"I don't understand sentences that start with '{tok.value}'.", line=tok.line, column=tok.column)
        
    def parse_declare_or_function(self) -> Statement:
        # "create" ["a"|"an"] "variable" "called" NAME "with" "value" expr
        # | "create" ["a"|"an"] "function" "called" NAME ...
        start = self.next_token() # create
        if self.peek().value.lower() in ('a', 'an'):
            self.next_token()
            
        kind = self.consume('KEYWORD').value.lower()
        if kind == 'variable':
            self.consume('KEYWORD', 'called')
            name = self.consume('IDENT').value
            self.consume('KEYWORD', 'with')
            self.consume('KEYWORD', 'value')
            expr = self.parse_expr()
            self.consume('PERIOD')
            return Declare(line=start.line, column=start.column, name=name, value=expr)
        elif kind == 'function':
            pass # TODO function parsing
            
        raise CompileError(f"Expected 'variable' or 'function' after 'create', got '{kind}'", line=start.line, column=start.column)
        
    def parse_let(self) -> Declare:
        start = self.next_token() # let
        name = self.consume('IDENT').value
        self.consume('KEYWORD', 'be')
        expr = self.parse_expr()
        self.consume('PERIOD')
        return Declare(line=start.line, column=start.column, name=name, value=expr)
        
    def parse_set(self) -> SetStmt:
        start = self.next_token() # set
        target = self.parse_target()
        self.consume('KEYWORD', 'to')
        expr = self.parse_expr()
        self.consume('PERIOD')
        return SetStmt(line=start.line, column=start.column, target=target, value=expr)

    def parse_show(self) -> Show:
        start = self.next_token() # show
        exprs = [self.parse_expr()]
        # show expr { "followed" "by" expr }
        while self.match_keyword('followed'):
            self.consume('KEYWORD', 'by')
            exprs.append(self.parse_expr())
        self.consume('PERIOD')
        return Show(line=start.line, column=start.column, exprs=exprs)

    def parse_expr(self) -> Expr:
        return self.parse_additive() # TODO: implement full expression hierarchy
        
    def parse_additive(self) -> Expr:
        return self.parse_primary() # TODO
        
    def parse_primary(self) -> Expr:
        tok = self.peek()
        if tok.type == 'NUMBER':
            self.next_token()
            return Literal(line=tok.line, column=tok.column, value=float(tok.value) if '.' in tok.value else int(tok.value))
        elif tok.type == 'STRING':
            self.next_token()
            return Literal(line=tok.line, column=tok.column, value=tok.value)
        elif tok.type == 'IDENT':
            self.next_token()
            return Identifier(line=tok.line, column=tok.column, name=tok.value)
            
        raise CompileError(f"Unexpected token in expression: {tok.value}", line=tok.line, column=tok.column)
        
    def parse_target(self) -> Expr:
        tok = self.peek()
        if tok.type == 'IDENT':
            self.next_token()
            return Identifier(line=tok.line, column=tok.column, name=tok.value)
        # TODO handle 'item expr of name', etc
        raise CompileError(f"Expected a target variable, got {tok.value}", line=tok.line, column=tok.column)
