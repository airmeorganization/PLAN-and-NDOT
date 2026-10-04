from typing import List, NamedTuple
from common.diagnostics import CompileError

class Token(NamedTuple):
    type: str     # 'SEGMENT' or 'TERMINATOR' or 'EOF'
    value: str    # The digit string
    line: int
    column: int
    
class Lexer:
    """N-DOT Lexer: Processes digit streams separated by dots."""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        
    def tokenize(self) -> List[Token]:
        tokens = []
        line_num = 1
        column = 1
        current_segment = []
        
        def emit_segment(col_start):
            if not current_segment:
                return
            val = "".join(current_segment)
            if val == "0":
                tokens.append(Token("TERMINATOR", val, line_num, col_start))
            else:
                tokens.append(Token("SEGMENT", val, line_num, col_start))
            current_segment.clear()

        segment_start_col = 1
        
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
                if not current_segment:
                    segment_start_col = column
                current_segment.append(char)
                column += 1
                continue
                
            if char == '.':
                emit_segment(segment_start_col)
                column += 1
                continue
                
            # If we get here, it's an invalid character
            lines = self.source_code.split('\n')
            source_line = lines[line_num - 1] if line_num <= len(lines) else ""
            raise CompileError(
                f"Invalid character '{char}' in N-DOT source. Only digits, dots, and whitespace are allowed.",
                line=line_num,
                column=column,
                source_line=source_line
            )
            
        # Emit final segment if any
        emit_segment(segment_start_col)
        tokens.append(Token("EOF", "", line_num, column))
        return tokens
