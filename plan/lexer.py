import re
from typing import List, NamedTuple, Optional
from common.diagnostics import CompileError

class Token(NamedTuple):
    type: str
    value: str
    line: int
    column: int
    indent: int
    raw_value: str

class Lexer:
    """PLAN Lexer: Tokenizes controlled-English source into tokens with line, column, and indentation."""

    RESERVED_KEYWORDS = {
        'create', 'let', 'set', 'increase', 'decrease', 'add', 'append', 'remove',
        'show', 'ask', 'use', 'return', 'call', 'stop', 'skip', 'when', 'if',
        'otherwise', 'for', 'every', 'while', 'repeat', 'try', 'on', 'end',
        'note', 'python', 'is', 'not', 'and', 'or', 'plus', 'minus', 'times',
        'divided', 'by', 'modulo', 'power', 'of', 'to', 'from', 'in',
        'true', 'false', 'yes', 'no', 'nothing', 'it', 'with', 'called',
        'value', 'be', 'store', 'the', 'answer', 'shared', 'failure', 'as',
        'gives', 'back', 'accepts', 'that', 'empty', 'first', 'last', 'item',
        'entry', 'between', 'contains', 'greater', 'less', 'more', 'fewer',
        'equal', 'at', 'least', 'most', 'followed', 'steps', 'round', 'loop',
        'program', 'result', 'a', 'an'
    }

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        lines = self.source_code.splitlines(keepends=True)
        tokens: List[Token] = []

        line_num = 1
        i = 0
        total_len = len(self.source_code)

        while i < total_len:
            # Check for python: escape block at start of line (or after spaces)
            # e.g. python:\n    code...
            current_line_start = self.source_code.rfind('\n', 0, i) + 1
            col = i - current_line_start + 1
            prefix = self.source_code[i:]

            # Check for Note: comment
            if re.match(r'^[Nn][Oo][Tt][Ee]:', prefix):
                # Skip to end of line
                eol = self.source_code.find('\n', i)
                if eol == -1:
                    break
                i = eol + 1
                line_num += 1
                continue

            # Check for Python escape block
            py_match = re.match(r'^[Pp][Yy][Tt][Hh][Oo][Nn]:(?:\r?\n[ \t]+.*)+', prefix)
            if py_match:
                block_text = py_match.group(0)
                indent = col - 1
                tokens.append(Token('PYTHON_BLOCK', block_text, line_num, col, indent, block_text))
                line_count = block_text.count('\n')
                line_num += line_count
                i += len(block_text)
                continue

            # Whitespace & Newlines
            ch = self.source_code[i]
            if ch == '\r':
                i += 1
                continue
            if ch == '\n':
                line_num += 1
                i += 1
                continue
            if ch in (' ', '\t'):
                i += 1
                continue

            # Compute current line indentation
            line_indent = self._calc_line_indent(current_line_start)

            # Possessive: 's directly after a word
            if prefix.startswith("'s") or prefix.startswith("’s"):
                tokens.append(Token('POSSESSIVE', "'s", line_num, col, line_indent, "'s"))
                i += 2
                continue

            # String literal: "..."
            if ch == '"':
                str_val, end_idx, lines_crossed = self._lex_string(i, line_num, col)
                tokens.append(Token('STRING', str_val, line_num, col, line_indent, str_val))
                line_num += lines_crossed
                i = end_idx
                continue

            # Number: Decimal (e.g. 3.14) or Integer (e.g. 19), with optional leading minus sign
            # Note: 5. followed by space or EOF must be Integer(5) then Period(.)
            num_match = re.match(r'^-?(\d+\.\d+|\d+)', prefix)
            if num_match:
                num_str = num_match.group(0)
                tokens.append(Token('NUMBER', num_str, line_num, col, line_indent, num_str))
                i += len(num_str)
                continue

            # Math operators (+, *, /, %, **, comparisons)
            if ch == '+':
                tokens.append(Token('KEYWORD', 'plus', line_num, col, line_indent, '+'))
                i += 1
                continue

            if ch == '*':
                if i + 1 < n and self.source[i + 1] == '*':
                    tokens.append(Token('KEYWORD', 'power', line_num, col, line_indent, '**'))
                    i += 2
                    continue
                tokens.append(Token('KEYWORD', 'times', line_num, col, line_indent, '*'))
                i += 1
                continue

            if ch == '/':
                tokens.append(Token('KEYWORD', 'divided_op', line_num, col, line_indent, '/'))
                i += 1
                continue

            if ch == '%':
                tokens.append(Token('KEYWORD', 'modulo', line_num, col, line_indent, '%'))
                i += 1
                continue

            if ch in ('=', '!', '<', '>'):
                if prefix.startswith('=='):
                    tokens.append(Token('KEYWORD', '==', line_num, col, line_indent, '=='))
                    i += 2
                    continue
                elif prefix.startswith('!='):
                    tokens.append(Token('KEYWORD', '!=', line_num, col, line_indent, '!='))
                    i += 2
                    continue
                elif prefix.startswith('>='):
                    tokens.append(Token('KEYWORD', '>=', line_num, col, line_indent, '>='))
                    i += 2
                    continue
                elif prefix.startswith('<='):
                    tokens.append(Token('KEYWORD', '<=', line_num, col, line_indent, '<='))
                    i += 2
                    continue
                elif ch == '>':
                    tokens.append(Token('KEYWORD', '>', line_num, col, line_indent, '>'))
                    i += 1
                    continue
                elif ch == '<':
                    tokens.append(Token('KEYWORD', '<', line_num, col, line_indent, '<'))
                    i += 1
                    continue

            # Minus sign / dash
            if ch == '-':
                tokens.append(Token('MINUS', '-', line_num, col, line_indent, '-'))
                i += 1
                continue

            # Comma
            if ch == ',':
                tokens.append(Token('COMMA', ',', line_num, col, line_indent, ','))
                i += 1
                continue

            # Period (End of sentence)
            if ch == '.':
                tokens.append(Token('PERIOD', '.', line_num, col, line_indent, '.'))
                i += 1
                continue

            # Parentheses
            if ch == '(':
                tokens.append(Token('LPAREN', '(', line_num, col, line_indent, '('))
                i += 1
                continue
            if ch == ')':
                tokens.append(Token('RPAREN', ')', line_num, col, line_indent, ')'))
                i += 1
                continue

            # Colon
            if ch == ':':
                tokens.append(Token('COLON', ':', line_num, col, line_indent, ':'))
                i += 1
                continue

            # Word / Identifier (possibly dotted inside module names like os.path)
            word_match = re.match(r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*', prefix)
            if word_match:
                raw_word = word_match.group(0)
                # But if it ends with a period, don't include the period in the word
                if raw_word.endswith('.'):
                    raw_word = raw_word[:-1]

                lower_word = raw_word.lower()
                tok_type = 'KEYWORD' if lower_word in self.RESERVED_KEYWORDS else 'IDENT'
                tokens.append(Token(tok_type, lower_word, line_num, col, line_indent, raw_word))
                i += len(raw_word)
                continue

            # If unrecognized character
            raise CompileError(
                f"Line {line_num}: I don't recognise the character '{ch}'.",
                line=line_num,
                column=col,
                source_line=self._get_line(line_num)
            )

        last_col = col if 'col' in locals() else 1
        last_indent = line_indent if 'line_indent' in locals() else 0
        tokens.append(Token('EOF', '', line_num, last_col, last_indent, ''))
        self.tokens = tokens
        return tokens

    def _calc_line_indent(self, line_start: int) -> int:
        spaces = 0
        idx = line_start
        while idx < len(self.source_code):
            c = self.source_code[idx]
            if c == ' ':
                spaces += 1
            elif c == '\t':
                spaces += 4
            elif c in ('\r', '\n'):
                return 0
            else:
                break
            idx += 1
        return spaces

    def _lex_string(self, start_idx: int, line: int, col: int):
        chars = []
        i = start_idx + 1
        lines_crossed = 0
        while i < len(self.source_code):
            c = self.source_code[i]
            if c == '\n':
                lines_crossed += 1
            if c == '\\':
                i += 1
                if i >= len(self.source_code):
                    break
                esc = self.source_code[i]
                if esc == 'n':
                    chars.append('\n')
                elif esc == 't':
                    chars.append('\t')
                elif esc == '"':
                    chars.append('"')
                elif esc == '\\':
                    chars.append('\\')
                else:
                    chars.append(esc)
                i += 1
                continue
            if c == '"':
                return "".join(chars), i + 1, lines_crossed
            chars.append(c)
            i += 1

        raise CompileError(f"Line {line}: this text is never closed — add a '\"' at the end.", line=line, column=col)

    def _get_line(self, line_num: int) -> str:
        lines = self.source_code.splitlines()
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1]
        return ""
