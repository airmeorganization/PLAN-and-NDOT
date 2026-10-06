from typing import List, NamedTuple
from common.diagnostics import CompileError

class Token(NamedTuple):
    type: str     # 'SEGMENT' or 'TERMINATOR' or 'EOF'
    value: str    # The digit string
    line: int
    column: int
    
class Lexer:
    """N-DOT Lexer: Processes digit streams separated by dots.

    Implements lexical checks:
    - N101: Illegal character (anything except digits, dots, whitespace)
    - N102: Empty segment ('..', leading or trailing '.')
    - N103: Leading zero in a segment (e.g. '05')
    - N104: Program does not end with the terminator '0'
    """

    def __init__(self, source_code: str):
        self.source_code = source_code

    def tokenize(self) -> List[Token]:
        tokens = []
        line_num = 1
        column = 1
        current_segment = []
        segment_start_col = 1
        saw_dot = False
        saw_non_whitespace = False

        def emit_segment(col_start):
            nonlocal saw_dot
            if not current_segment:
                return
            val = "".join(current_segment)
            if len(val) > 1 and val.startswith("0"):
                lines = self.source_code.split('\n')
                source_line = lines[line_num - 1] if line_num <= len(lines) else ""
                raise CompileError(
                    f"Leading zero in segment '{val}'",
                    line=line_num,
                    column=col_start,
                    code="N103",
                    source_line=source_line
                )
            if val == "0":
                tokens.append(Token("TERMINATOR", val, line_num, col_start))
            else:
                tokens.append(Token("SEGMENT", val, line_num, col_start))
            current_segment.clear()
            saw_dot = False

        for char in self.source_code:
            if char.isspace():
                if char == '\n':
                    emit_segment(segment_start_col)
                    line_num += 1
                    column = 1
                else:
                    column += 1
                continue

            if char.isdigit():
                saw_non_whitespace = True
                saw_dot = False
                if not current_segment:
                    segment_start_col = column
                current_segment.append(char)
                column += 1
                continue

            if char == '.':
                if not saw_non_whitespace or saw_dot or not current_segment:
                    lines = self.source_code.split('\n')
                    source_line = lines[line_num - 1] if line_num <= len(lines) else ""
                    raise CompileError(
                        "Empty segment in N-DOT source (consecutive or leading dot)",
                        line=line_num,
                        column=column,
                        code="N102",
                        source_line=source_line
                    )
                saw_non_whitespace = True
                emit_segment(segment_start_col)
                saw_dot = True
                column += 1
                continue

            # If we get here, it's an invalid character (N101)
            lines = self.source_code.split('\n')
            source_line = lines[line_num - 1] if line_num <= len(lines) else ""
            raise CompileError(
                f"Invalid character '{char}' in N-DOT source. Only digits, dots, and whitespace are allowed.",
                line=line_num,
                column=column,
                code="N101",
                source_line=source_line
            )

        # If ended with a trailing dot:
        if saw_dot:
            lines = self.source_code.split('\n')
            source_line = lines[line_num - 1] if line_num <= len(lines) else ""
            raise CompileError(
                "Empty segment in N-DOT source (trailing dot)",
                line=line_num,
                column=column - 1,
                code="N102",
                source_line=source_line
            )

        # Emit final segment if any
        emit_segment(segment_start_col)

        # Check N104: Program must end with terminator '0'
        if tokens:
            if tokens[-1].type != 'TERMINATOR':
                raise CompileError(
                    "Program does not end with the terminator '0'",
                    line=tokens[-1].line,
                    column=tokens[-1].column,
                    code="N104"
                )
        elif saw_non_whitespace:
            raise CompileError(
                "Program does not end with the terminator '0'",
                line=line_num,
                column=column,
                code="N104"
            )

        tokens.append(Token("EOF", "", line_num, column))
        return tokens
