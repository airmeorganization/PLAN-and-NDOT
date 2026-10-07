from typing import List, Optional, Tuple, Dict
from plan.lexer import Token
from plan.ast_nodes import *
from common.diagnostics import CompileError

class Parser:
    """PLAN Recursive Descent Parser implementing the full v0.1 grammar from spec/PLAN.md."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1] # EOF

    def peek_next(self) -> Token:
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return self.tokens[-1]

    def next_token(self) -> Token:
        tok = self.peek()
        if tok.type != 'EOF':
            self.pos += 1
        return tok

    def match(self, expected_type: str, expected_val: Optional[str] = None) -> bool:
        tok = self.peek()
        if tok.type == expected_type and (expected_val is None or tok.value == expected_val.lower()):
            self.pos += 1
            return True
        return False

    def match_word(self, word: str) -> bool:
        tok = self.peek()
        if (tok.type in ('KEYWORD', 'IDENT')) and tok.value == word.lower():
            self.pos += 1
            return True
        return False

    def match_words(self, *words: str) -> bool:
        # Check if following sequence of words matches without advancing unless all match
        saved = self.pos
        for w in words:
            tok = self.peek()
            if (tok.type in ('KEYWORD', 'IDENT')) and tok.value == w.lower():
                self.pos += 1
            else:
                self.pos = saved
                return False
        return True

    def consume(self, expected_type: str, expected_val: Optional[str] = None) -> Token:
        tok = self.peek()
        if tok.type == expected_type and (expected_val is None or tok.value == expected_val.lower()):
            return self.next_token()

        exp_msg = expected_type if not expected_val else f"'{expected_val}'"
        raise CompileError(
            f"Line {tok.line}: Expected {exp_msg}, but got '{tok.raw_value}'.",
            line=tok.line, column=tok.column
        )

    def consume_word(self, word: str) -> Token:
        tok = self.peek()
        if (tok.type in ('KEYWORD', 'IDENT')) and tok.value == word.lower():
            return self.next_token()
        raise CompileError(
            f"Line {tok.line}: Expected '{word}', but got '{tok.raw_value}'.",
            line=tok.line, column=tok.column
        )

    # --- Program and Sentence Dispatch ---

    def parse_program(self) -> Program:
        statements = []
        while self.peek().type != 'EOF':
            stmt = self.parse_sentence()
            if stmt:
                statements.append(stmt)
        return Program(line=1, column=1, statements=statements)

    def parse_sentence(self) -> Statement:
        tok = self.peek()

        if tok.type == 'PYTHON_BLOCK':
            self.next_token()
            code = tok.value
            colon_idx = code.find(':')
            raw_code = code[colon_idx + 1:].strip('\r\n')
            lines = raw_code.splitlines()
            if lines:
                indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
                min_indent = min(indents) if indents else 0
                raw_code = "\n".join(l[min_indent:] if len(l) >= min_indent else l for l in lines)
            return PythonRaw(line=tok.line, column=tok.column, code=raw_code)

        # Check for block starters
        w = tok.value.lower()
        if w in ('when', 'if'):
            return self.parse_when()
        elif w == 'for':
            return self.parse_for()
        elif w in ('while', 'as'):
            return self.parse_while()
        elif w == 'repeat':
            return self.parse_repeat()
        elif w == 'try':
            return self.parse_try()
        elif w == 'create':
            # Could be "create variable" or "create function"
            return self.parse_create()
        elif w == 'let':
            return self.parse_let()
        elif w == 'set':
            return self.parse_set()
        elif w == 'increase':
            return self.parse_increase()
        elif w == 'decrease':
            return self.parse_decrease()
        elif w == 'add':
            return self.parse_add()
        elif w == 'append':
            return self.parse_append()
        elif w == 'remove':
            return self.parse_remove()
        elif w == 'show':
            return self.parse_show()
        elif w == 'ask':
            return self.parse_ask()
        elif w == 'use':
            return self.parse_use()
        elif w == 'return':
            return self.parse_return()
        elif w == 'call':
            return self.parse_call_stmt()
        elif w == 'stop':
            return self.parse_stop()
        elif w == 'skip':
            return self.parse_skip()
        elif w == 'end':
            # Stray End statement handled by block parsers; if here, consume and warn/ignore
            return self.parse_end_stmt()

        raise CompileError(
            f"Line {tok.line}: I don't understand sentences that start with '{tok.raw_value}'.",
            line=tok.line, column=tok.column
        )

    # --- Statement Parsers ---

    def parse_create(self) -> Statement:
        start = self.next_token() # 'create'
        if self.peek().value in ('a', 'an'):
            self.next_token()

        kind_tok = self.peek()
        kind = kind_tok.value.lower()

        if kind == 'variable':
            self.next_token()
            self.consume_word('called')
            name_tok = self.consume_ident()
            self.consume_word('with')
            self.consume_word('value')
            val_expr = self.parse_expr()
            self.consume('PERIOD')
            return Declare(line=start.line, column=start.column, name=name_tok.raw_value, value=val_expr)

        elif kind == 'function':
            self.next_token()
            self.consume_word('called')
            name_tok = self.consume_ident()

            params = []
            if self.match_words('that', 'accepts'):
                params.append(self.parse_param())
                while True:
                    if self.peek().value == 'and' and self.peek_next().value == 'gives':
                        break
                    if self.peek().type == 'COMMA':
                        next_tok = self.peek_next()
                        if next_tok.value == 'and' and self.pos + 2 < len(self.tokens) and self.tokens[self.pos + 2].value == 'gives':
                            break
                        # If next token is on next line, comma is header delimiter
                        if next_tok.line != self.peek().line or next_tok.value in ('gives', 'return', 'when', 'if', 'show', 'let', 'create', 'set'):
                            break
                        self.next_token() # consume COMMA
                        self.match_word('and')
                        params.append(self.parse_param())
                    elif self.match_word('and'):
                        params.append(self.parse_param())
                    else:
                        break

            ret_type = None
            if self.match_words('and', 'gives', 'back'):
                ret_type = self.parse_type()

            # Function block header can end with ',' or '.'
            if not (self.match('COMMA') or self.match('PERIOD')):
                raise CompileError(f"Line {start.line}: expected ',' or '.' after function header.", line=start.line, column=start.column)

            body = self.parse_body(header_indent=start.indent, block_kind='function')
            return FunctionDef(line=start.line, column=start.column, name=name_tok.raw_value, params=params, return_type=ret_type, body=body)

        raise CompileError(f"Line {kind_tok.line}: Expected 'variable' or 'function' after 'create', got '{kind_tok.raw_value}'.", line=kind_tok.line, column=kind_tok.column)

    def parse_param(self) -> Tuple[Optional[str], str]:
        # param = [TYPE] NAME
        # Check if type is present
        ptype = self.try_parse_type()
        name_tok = self.consume_ident()
        return (ptype, name_tok.raw_value)

    def parse_type(self) -> str:
        ptype = self.try_parse_type()
        if not ptype:
            tok = self.peek()
            raise CompileError(f"Line {tok.line}: Expected type, got '{tok.raw_value}'.", line=tok.line, column=tok.column)
        return ptype

    def try_parse_type(self) -> Optional[str]:
        if self.match_words('whole', 'number'):
            return 'int'
        for t in ('number', 'text', 'list', 'dictionary', 'flag'):
            if self.match_word(t):
                mapping = {'number': 'float', 'text': 'str', 'list': 'list', 'dictionary': 'dict', 'flag': 'bool'}
                return mapping[t]
        return None

    def parse_let(self) -> Declare:
        start = self.next_token() # 'let'
        name_tok = self.consume_ident()
        self.consume_word('be')
        val_expr = self.parse_expr()
        self.consume('PERIOD')
        return Declare(line=start.line, column=start.column, name=name_tok.raw_value, value=val_expr)

    def parse_set(self) -> SetStmt:
        start = self.next_token() # 'set'
        target = self.parse_target()
        self.consume_word('to')
        val_expr = self.parse_expr()
        self.consume('PERIOD')
        return SetStmt(line=start.line, column=start.column, target=target, value=val_expr)

    def parse_increase(self) -> ModifyStmt:
        start = self.next_token() # 'increase'
        target = self.parse_target()
        self.consume_word('by')
        val_expr = self.parse_expr()
        self.consume('PERIOD')
        return ModifyStmt(line=start.line, column=start.column, target=target, op='+', value=val_expr)

    def parse_decrease(self) -> ModifyStmt:
        start = self.next_token() # 'decrease'
        target = self.parse_target()
        self.consume_word('by')
        val_expr = self.parse_expr()
        self.consume('PERIOD')
        return ModifyStmt(line=start.line, column=start.column, target=target, op='-', value=val_expr)

    def parse_add(self) -> ModifyStmt:
        start = self.next_token() # 'add'
        val_expr = self.parse_expr()
        self.consume_word('to')
        target = self.parse_target()
        self.consume('PERIOD')
        return ModifyStmt(line=start.line, column=start.column, target=target, op='+', value=val_expr)

    def parse_append(self) -> ModifyStmt:
        start = self.next_token() # 'append'
        val_expr = self.parse_expr()
        self.consume_word('to')
        target = self.parse_target()
        self.consume('PERIOD')
        return ModifyStmt(line=start.line, column=start.column, target=target, op='append', value=val_expr)

    def parse_remove(self) -> ModifyStmt:
        start = self.next_token() # 'remove'
        val_expr = self.parse_expr()
        self.consume_word('from')
        target = self.parse_target()
        self.consume('PERIOD')
        return ModifyStmt(line=start.line, column=start.column, target=target, op='remove', value=val_expr)

    def parse_show(self) -> Show:
        start = self.next_token() # 'show'
        exprs = [self.parse_expr()]
        followed_by = False
        while self.match_words('followed', 'by'):
            followed_by = True
            exprs.append(self.parse_expr())
        self.consume('PERIOD')
        return Show(line=start.line, column=start.column, exprs=exprs, followed_by=followed_by)

    def parse_ask(self) -> Ask:
        start = self.next_token() # 'ask'
        kind = 'text'
        if self.match_words('for', 'a', 'number', 'with'):
            kind = 'number'
        elif self.match_words('for', 'a', 'whole', 'number', 'with'):
            kind = 'whole_number'
        elif self.match_word('with'):
            kind = 'text'

        prompt_expr = self.parse_expr()
        self.consume_word('and')
        self.consume_word('store')
        if self.match_words('the', 'answer'):
            pass
        elif self.match_word('the'):
            self.consume_word('answer')
        elif self.match_word('answer'):
            pass
        self.consume_word('in')
        target_tok = self.consume_ident()
        self.consume('PERIOD')
        return Ask(line=start.line, column=start.column, prompt=prompt_expr, target=target_tok.raw_value, kind=kind)

    def parse_use(self) -> Statement:
        start = self.next_token() # 'use'
        if self.match_words('the', 'shared', 'variable'):
            name_tok = self.consume_ident()
            self.consume('PERIOD')
            return UseShared(line=start.line, column=start.column, name=name_tok.raw_value)

        # Check for "use NAME { , and NAME } from [the] MODULE module."
        saved = self.pos
        if self.peek().value not in ('the',):
            first_name = self.consume_ident()
            names = [first_name.raw_value]
            while self.match('COMMA') or self.match_word('and'):
                self.match_word('and')
                names.append(self.consume_ident().raw_value)
            if self.match_word('from'):
                if self.peek().value == 'the':
                    self.next_token()
                mod_tok = self.consume_ident()
                self.consume_word('module')
                self.consume('PERIOD')
                return UseFromModule(line=start.line, column=start.column, names=names, module=mod_tok.raw_value)

        # Fallback to "use [the] MODULE module [as NAME]."
        self.pos = saved
        if self.peek().value == 'the':
            self.next_token()
        mod_tok = self.consume_ident()
        self.consume_word('module')
        alias = None
        if self.match_word('as'):
            alias = self.consume_ident().raw_value
        self.consume('PERIOD')
        return UseModule(line=start.line, column=start.column, module=mod_tok.raw_value, alias=alias)

    def parse_return(self) -> Return:
        start = self.next_token() # 'return'
        if self.match_word('nothing'):
            self.consume('PERIOD')
            return Return(line=start.line, column=start.column, value=None)
        if self.peek().type == 'PERIOD':
            self.next_token()
            return Return(line=start.line, column=start.column, value=None)
        val = self.parse_expr()
        self.consume('PERIOD')
        return Return(line=start.line, column=start.column, value=val)

    def parse_call_stmt(self) -> CallStmt:
        start = self.peek()
        call_expr = self.parse_call()
        self.consume('PERIOD')
        return CallStmt(line=start.line, column=start.column, call=call_expr)

    def parse_stop(self) -> Stop:
        start = self.next_token() # 'stop'
        if self.peek().value == 'the':
            self.next_token()
        target_tok = self.consume_word_in('loop', 'program')
        self.consume('PERIOD')
        return Stop(line=start.line, column=start.column, target=target_tok.value.lower())

    def parse_skip(self) -> Skip:
        start = self.next_token() # 'skip'
        if self.match_words('to', 'the', 'next', 'round') or self.match_words('this', 'round'):
            pass
        self.consume('PERIOD')
        return Skip(line=start.line, column=start.column)

    def parse_end_stmt(self) -> Statement:
        start = self.next_token() # 'end'
        self.next_token() # loop/when/function/etc
        self.consume('PERIOD')
        return None

    # --- Block Parsers ---

    def parse_when(self) -> WhenBlock:
        start = self.next_token() # 'when' or 'if'
        cond = self.parse_condition()
        self.consume('COMMA')
        body = self.parse_body(header_indent=start.indent, block_kind='when')
        cases = [WhenCase(condition=cond, body=body)]
        otherwise_body = None

        # Check for otherwise when / otherwise
        while self.match_word('otherwise'):
            if self.match_word('when') or self.match_word('if'):
                alt_cond = self.parse_condition()
                self.consume('COMMA')
                alt_body = self.parse_body(header_indent=start.indent, block_kind='when')
                cases.append(WhenCase(condition=alt_cond, body=alt_body))
            elif self.match('COMMA'):
                otherwise_body = self.parse_body(header_indent=start.indent, block_kind='when')
                break

        return WhenBlock(line=start.line, column=start.column, cases=cases, otherwise_body=otherwise_body)

    def parse_for(self) -> Statement:
        start = self.next_token() # 'for'
        self.consume_word('every')
        var_tok = self.consume_ident()

        if self.match_word('from'):
            start_expr = self.parse_expr()
            self.consume_word('to')
            end_expr = self.parse_expr()
            step_expr = None
            if self.match_words('in', 'steps', 'of'):
                step_expr = self.parse_expr()
            self.consume('COMMA')
            body = self.parse_body(header_indent=start.indent, block_kind='for')
            return ForRange(line=start.line, column=start.column, var_name=var_tok.raw_value, start=start_expr, end=end_expr, step=step_expr, body=body)

        elif self.match_word('in'):
            iter_expr = self.parse_expr()
            self.consume('COMMA')
            body = self.parse_body(header_indent=start.indent, block_kind='for')
            return ForEach(line=start.line, column=start.column, var_name=var_tok.raw_value, iterable=iter_expr, body=body)

        raise CompileError(f"Line {start.line}: Expected 'from' or 'in' after 'for every {var_tok.raw_value}'.", line=start.line, column=start.column)

    def parse_while(self) -> WhileLoop:
        start = self.next_token() # 'while' or 'as'
        if start.value.lower() == 'as':
            self.consume_word('long')
            self.consume_word('as')
        cond = self.parse_condition()
        self.consume('COMMA')
        body = self.parse_body(header_indent=start.indent, block_kind='while')
        return WhileLoop(line=start.line, column=start.column, condition=cond, body=body)

    def parse_repeat(self) -> RepeatLoop:
        start = self.next_token() # 'repeat'
        count_expr = self.parse_additive(allow_times=False)
        self.consume_word('times')
        self.consume('COMMA')
        body = self.parse_body(header_indent=start.indent, block_kind='repeat')
        return RepeatLoop(line=start.line, column=start.column, count=count_expr, body=body)

    def parse_try(self) -> TryBlock:
        start = self.next_token() # 'try'
        self.consume('COMMA')
        try_body = self.parse_body(header_indent=start.indent, block_kind='try')

        self.consume_word('on')
        self.consume_word('failure')
        fail_name = None
        if self.match_word('as'):
            fail_name = self.consume_ident().raw_value
        self.consume('COMMA')
        fail_body = self.parse_body(header_indent=start.indent, block_kind='try')
        return TryBlock(line=start.line, column=start.column, try_body=try_body, failure_name=fail_name, failure_body=fail_body)

    def parse_body(self, header_indent: int, block_kind: str) -> List[Statement]:
        """Parses a block body: supports inline, indented, and terminated forms."""
        # 1. Inline form: statement is on the same line as the header comma
        tok = self.peek()
        if tok.type != 'EOF' and tok.line == self.tokens[self.pos - 1].line:
            # Inline statement
            stmt = self.parse_sentence()
            return [stmt] if stmt else []

        # 2. Indented or Terminated form
        body: List[Statement] = []
        is_indented = tok.indent > header_indent

        while self.peek().type != 'EOF':
            cur = self.peek()

            # Check for End <block_kind>.
            if cur.value.lower() == 'end':
                # Check what follows
                next_tok = self.peek_next()
                if next_tok.value.lower() in (block_kind, 'loop'):
                    self.next_token() # 'end'
                    self.next_token() # kind
                    self.consume('PERIOD')
                    return body

            # If indented, block ends when indentation drops back to <= header_indent
            if is_indented and cur.indent <= header_indent:
                break

            stmt = self.parse_sentence()
            if stmt:
                body.append(stmt)

        return body

    # --- Expressions ---

    def parse_condition(self) -> Expr:
        return self.parse_expr()

    def parse_expr(self) -> Expr:
        return self.parse_or()

    def parse_or(self) -> Expr:
        left = self.parse_and()
        while self.match_word('or'):
            right = self.parse_and()
            left = BinaryOp(line=left.line, column=left.column, left=left, op='or', right=right)
        return left

    def parse_and(self) -> Expr:
        left = self.parse_not()
        while self.peek().value == 'and':
            # Do not consume 'and' if followed by statement connectors like 'store' or 'gives'
            if self.peek_next().value in ('store', 'gives'):
                break
            self.next_token() # consume 'and'
            right = self.parse_not()
            left = BinaryOp(line=left.line, column=left.column, left=left, op='and', right=right)
        return left

    def parse_not(self) -> Expr:
        if self.match_word('not'):
            tok = self.tokens[self.pos - 1]
            opnd = self.parse_not()
            return UnaryOp(line=tok.line, column=tok.column, op='not', operand=opnd)
        return self.parse_comparison()

    def parse_comparison(self) -> Expr:
        left = self.parse_additive()

        # Check for comparison operators
        if self.match_words('is', 'greater', 'than', 'or', 'equal', 'to') or self.match_words('is', 'at', 'least') or self.match_word('>='):
            right = self.parse_additive()
            return BinaryOp(line=left.line, column=left.column, left=left, op='>=', right=right)
        elif self.match_words('is', 'less', 'than', 'or', 'equal', 'to') or self.match_words('is', 'at', 'most') or self.match_word('<='):
            right = self.parse_additive()
            return BinaryOp(line=left.line, column=left.column, left=left, op='<=', right=right)
        elif self.match_words('is', 'greater', 'than') or self.match_words('is', 'more', 'than') or self.match_word('>'):
            right = self.parse_additive()
            return BinaryOp(line=left.line, column=left.column, left=left, op='>', right=right)
        elif self.match_words('is', 'less', 'than') or self.match_words('is', 'fewer', 'than') or self.match_word('<'):
            right = self.parse_additive()
            return BinaryOp(line=left.line, column=left.column, left=left, op='<', right=right)
        elif self.match_words('is', 'not', 'equal', 'to') or self.match_words('is', 'not') or self.match_word('!='):
            right = self.parse_additive()
            return BinaryOp(line=left.line, column=left.column, left=left, op='!=', right=right)
        elif self.match_words('is', 'equal', 'to') or self.match_word('equals') or self.match_word('is') or self.match_word('=='):
            # Check for "is between", "is empty", "is nothing", "is in"
            if self.match_word('between'):
                low = self.parse_additive()
                self.consume_word('and')
                high = self.parse_additive()
                return Between(line=left.line, column=left.column, expr=left, low=low, high=high, negated=False)
            elif self.match_word('empty'):
                return IsEmpty(line=left.line, column=left.column, expr=left, negated=False)
            elif self.match_word('nothing'):
                return IsNothing(line=left.line, column=left.column, expr=left, negated=False)
            elif self.match_word('in'):
                right = self.parse_additive()
                return BinaryOp(line=left.line, column=left.column, left=left, op='in', right=right)

            right = self.parse_additive()
            return BinaryOp(line=left.line, column=left.column, left=left, op='==', right=right)
        elif self.match_word('contains'):
            right = self.parse_additive()
            # "A contains B" means "B in A"
            return BinaryOp(line=left.line, column=left.column, left=right, op='in', right=left)

        return left

    def parse_additive(self, allow_times: bool = True) -> Expr:
        left = self.parse_multiplicative(allow_times=allow_times)
        while True:
            if self.match_word('plus'):
                right = self.parse_multiplicative(allow_times=allow_times)
                left = BinaryOp(line=left.line, column=left.column, left=left, op='+', right=right)
            elif self.match_word('minus') or self.match('MINUS'):
                right = self.parse_multiplicative(allow_times=allow_times)
                left = BinaryOp(line=left.line, column=left.column, left=left, op='-', right=right)
            else:
                break
        return left

    def parse_multiplicative(self, allow_times: bool = True) -> Expr:
        left = self.parse_power()
        while True:
            if allow_times and self.match_word('times'):
                right = self.parse_power()
                left = BinaryOp(line=left.line, column=left.column, left=left, op='*', right=right)
            elif self.match_words('divided', 'by') or self.match_word('divided_op'):
                right = self.parse_power()
                left = BinaryOp(line=left.line, column=left.column, left=left, op='/', right=right)
            elif self.match_word('modulo'):
                right = self.parse_power()
                left = BinaryOp(line=left.line, column=left.column, left=left, op='%', right=right)
            else:
                break
        return left

    def parse_power(self) -> Expr:
        left = self.parse_unary()
        if self.match_words('to', 'the', 'power', 'of') or self.match_word('power'):
            right = self.parse_power() # right-associative
            return BinaryOp(line=left.line, column=left.column, left=left, op='**', right=right)
        return left

    def parse_unary(self) -> Expr:
        if self.match_word('negative') or self.match('MINUS'):
            tok = self.tokens[self.pos - 1]
            opnd = self.parse_unary()
            return UnaryOp(line=tok.line, column=tok.column, op='-', operand=opnd)
        return self.parse_postfix()

    def parse_postfix(self) -> Expr:
        expr = self.parse_primary()

        # Handle postfix phrases
        while True:
            if self.match_words('rounded', 'to'):
                places = self.parse_additive()
                self.consume_word('places')
                expr = Phrase(line=expr.line, column=expr.column, name='rounded', args=[expr, places])
            elif self.match_word('rounded'):
                expr = Phrase(line=expr.line, column=expr.column, name='rounded', args=[expr])
            elif self.match_words('as', 'text'):
                expr = Phrase(line=expr.line, column=expr.column, name='as_text', args=[expr])
            elif self.match_words('as', 'a', 'whole', 'number'):
                expr = Phrase(line=expr.line, column=expr.column, name='as_whole_number', args=[expr])
            elif self.match_words('as', 'a', 'number'):
                expr = Phrase(line=expr.line, column=expr.column, name='as_number', args=[expr])
            elif self.match_words('in', 'uppercase'):
                expr = Phrase(line=expr.line, column=expr.column, name='uppercase', args=[expr])
            elif self.match_words('in', 'lowercase'):
                expr = Phrase(line=expr.line, column=expr.column, name='lowercase', args=[expr])
            elif self.match_word('sorted'):
                expr = Phrase(line=expr.line, column=expr.column, name='sorted', args=[expr])
            elif self.match_word('reversed'):
                expr = Phrase(line=expr.line, column=expr.column, name='reversed', args=[expr])
            elif self.match_words('split', 'by'):
                sep = self.parse_additive()
                expr = Phrase(line=expr.line, column=expr.column, name='split_by', args=[expr, sep])
            elif self.match_words('joined', 'with'):
                sep = self.parse_additive()
                expr = Phrase(line=expr.line, column=expr.column, name='joined_with', args=[expr, sep])
            else:
                break

        return expr

    def parse_primary(self) -> Expr:
        tok = self.peek()

        # Parenthesized expression
        if self.match('LPAREN'):
            expr = self.parse_expr()
            self.consume('RPAREN')
            return expr

        # Literals
        if tok.type == 'NUMBER':
            self.next_token()
            val = float(tok.value) if '.' in tok.value else int(tok.value)
            return Literal(line=tok.line, column=tok.column, value=val)

        if tok.type == 'STRING':
            self.next_token()
            return Literal(line=tok.line, column=tok.column, value=tok.value)

        w = tok.value.lower()
        if w in ('true', 'yes'):
            self.next_token()
            return Literal(line=tok.line, column=tok.column, value=True)
        if w in ('false', 'no'):
            self.next_token()
            return Literal(line=tok.line, column=tok.column, value=False)
        if w == 'nothing':
            self.next_token()
            return Literal(line=tok.line, column=tok.column, value=None)

        # Collections
        if self.match_words('an', 'empty', 'list'):
            return ListLiteral(line=tok.line, column=tok.column, items=[])
        if self.match_words('an', 'empty', 'dictionary'):
            return DictLiteral(line=tok.line, column=tok.column)
        if self.match_words('a', 'list', 'of'):
            items = [self.parse_additive()]
            while self.match('COMMA') or self.match_word('and'):
                self.match_word('and')
                items.append(self.parse_additive())
            return ListLiteral(line=tok.line, column=tok.column, items=items)

        # Indexing: "item expr of postfix", "the first/last item of postfix", "the expr entry of postfix"
        if self.match_word('item'):
            idx = self.parse_additive()
            self.consume_word('of')
            seq = self.parse_primary()
            return Index(line=tok.line, column=tok.column, target=seq, index=idx)

        if self.match_words('the', 'first', 'item', 'of'):
            seq = self.parse_primary()
            return FirstItem(line=tok.line, column=tok.column, target=seq)

        if self.match_words('the', 'last', 'item', 'of'):
            seq = self.parse_primary()
            return LastItem(line=tok.line, column=tok.column, target=seq)

        if self.match_words('the', 'entry', 'of'):
            key = self.parse_additive()
            self.consume_word('of')
            mapping = self.parse_primary()
            return EntryIndex(line=tok.line, column=tok.column, target=mapping, key=key)

        # Prefix phrases
        if self.match_words('square', 'root', 'of'):
            opnd = self.parse_unary()
            return Phrase(line=tok.line, column=tok.column, name='square_root', args=[opnd])
        if self.match_words('absolute', 'value', 'of'):
            opnd = self.parse_unary()
            return Phrase(line=tok.line, column=tok.column, name='absolute_value', args=[opnd])
        if self.match_words('length', 'of') or self.match_words('the', 'number', 'of', 'items', 'in'):
            opnd = self.parse_unary()
            return Phrase(line=tok.line, column=tok.column, name='length_of', args=[opnd])
        if self.match_words('the', 'sum', 'of'):
            opnd = self.parse_unary()
            return Phrase(line=tok.line, column=tok.column, name='sum_of', args=[opnd])
        if self.match_words('the', 'largest', 'of'):
            opnd = self.parse_unary()
            return Phrase(line=tok.line, column=tok.column, name='largest_of', args=[opnd])
        if self.match_words('the', 'smallest', 'of'):
            opnd = self.parse_unary()
            return Phrase(line=tok.line, column=tok.column, name='smallest_of', args=[opnd])
        if self.match_words('the', 'average', 'of'):
            opnd = self.parse_unary()
            return Phrase(line=tok.line, column=tok.column, name='average_of', args=[opnd])
        if self.match_words('a', 'random', 'number', 'from'):
            a = self.parse_additive()
            self.consume_word('to')
            b = self.parse_additive()
            return Phrase(line=tok.line, column=tok.column, name='random_number', args=[a, b])
        if self.match_words('a', 'random', 'item', 'from'):
            coll = self.parse_unary()
            return Phrase(line=tok.line, column=tok.column, name='random_item', args=[coll])
        if self.match_words('the', 'current', 'time'):
            return Phrase(line=tok.line, column=tok.column, name='current_time', args=[])

        # Calls: "call callee with ..." or "the result of callee with ..."
        if self.match_word('call') or self.match_words('the', 'result', 'of'):
            return self.parse_call_args()

        # Identifiers and Possessive Member Access: NAME 's NAME
        if tok.type in ('IDENT', 'KEYWORD'):
            self.next_token()
            name_ident = Identifier(line=tok.line, column=tok.column, name=tok.raw_value)
            if self.match('POSSESSIVE'):
                member_tok = self.consume_ident()
                return MemberAccess(line=tok.line, column=tok.column, target=name_ident, member=member_tok.raw_value)
            return name_ident

        raise CompileError(f"Line {tok.line}: Unexpected token in expression: '{tok.raw_value}'.", line=tok.line, column=tok.column)

    def parse_call(self) -> Call:
        if self.match_word('call') or self.match_words('the', 'result', 'of'):
            pass
        return self.parse_call_args()

    def parse_call_args(self) -> Call:
        tok = self.peek()
        callee_ident = self.consume_ident()
        callee: Expr = Identifier(line=tok.line, column=tok.column, name=callee_ident.raw_value)
        if self.match('POSSESSIVE'):
            member_tok = self.consume_ident()
            callee = MemberAccess(line=tok.line, column=tok.column, target=callee, member=member_tok.raw_value)

        args = []
        kwargs = {}
        if self.match_word('with'):
            self.parse_one_arg(args, kwargs)
            while self.match('COMMA') or self.match_word('and'):
                self.match_word('and')
                self.parse_one_arg(args, kwargs)

        return Call(line=tok.line, column=tok.column, callee=callee, args=args, kwargs=kwargs)

    def parse_one_arg(self, args: List[Expr], kwargs: Dict[str, Expr]):
        # arg = additive | NAME "set" "to" additive
        tok = self.peek()
        next_tok = self.peek_next()
        if (tok.type in ('IDENT', 'KEYWORD')) and next_tok.value == 'set':
            kw_name = self.next_token().raw_value
            self.consume_word('set')
            self.consume_word('to')
            val = self.parse_additive()
            kwargs[kw_name] = val
        else:
            args.append(self.parse_additive())

    def parse_target(self) -> Expr:
        tok = self.peek()
        if self.match_word('item'):
            idx = self.parse_additive()
            self.consume_word('of')
            seq_tok = self.consume_ident()
            return Index(line=tok.line, column=tok.column, target=Identifier(line=seq_tok.line, column=seq_tok.column, name=seq_tok.raw_value), index=idx)

        if self.match_words('the', 'first', 'item', 'of'):
            seq_tok = self.consume_ident()
            return FirstItem(line=tok.line, column=tok.column, target=Identifier(line=seq_tok.line, column=seq_tok.column, name=seq_tok.raw_value))

        if self.match_words('the', 'last', 'item', 'of'):
            seq_tok = self.consume_ident()
            return LastItem(line=tok.line, column=tok.column, target=Identifier(line=seq_tok.line, column=seq_tok.column, name=seq_tok.raw_value))

        if self.match_words('the'):
            key = self.parse_additive()
            self.consume_word('entry')
            self.consume_word('of')
            map_tok = self.consume_ident()
            return EntryIndex(line=tok.line, column=tok.column, target=Identifier(line=map_tok.line, column=map_tok.column, name=map_tok.raw_value), key=key)

        ident_tok = self.consume_ident()
        ident = Identifier(line=ident_tok.line, column=ident_tok.column, name=ident_tok.raw_value)
        if self.match('POSSESSIVE'):
            member_tok = self.consume_ident()
            return MemberAccess(line=ident_tok.line, column=ident_tok.column, target=ident, member=member_tok.raw_value)
        return ident

    def consume_ident(self) -> Token:
        tok = self.peek()
        if tok.type in ('IDENT', 'KEYWORD'):
            return self.next_token()
        raise CompileError(f"Line {tok.line}: Expected an identifier, got '{tok.raw_value}'.", line=tok.line, column=tok.column)

    def consume_word_in(self, *choices: str) -> Token:
        tok = self.peek()
        if (tok.type in ('IDENT', 'KEYWORD')) and tok.value in choices:
            return self.next_token()
        raise CompileError(f"Line {tok.line}: Expected one of {choices}, got '{tok.raw_value}'.", line=tok.line, column=tok.column)
