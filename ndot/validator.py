from typing import List, NamedTuple, Optional
from plan.ast_nodes import ASTNode
from common.diagnostics import CompileError
from ndot.lexer import Token
from ndot.registry import Registry

class Instruction(NamedTuple):
    opcode: str
    operands: List[str]
    line: int
    column: int
    registry_entry: dict

class Validator:
    def __init__(self, registry: Registry):
        self.registry = registry
        
    def validate(self, tokens: List[Token]) -> List[Instruction]:
        instructions = []
        current_group = []
        
        for tok in tokens:
            if tok.type == 'EOF':
                break
                
            if tok.type == 'TERMINATOR':
                if not current_group:
                    raise CompileError("Empty instruction (0.0)", line=tok.line, column=tok.column)
                    
                opcode_tok = current_group[0]
                opcode_id = opcode_tok.value
                operands = [t.value for t in current_group[1:]]
                
                entry = self.registry.get_opcode(opcode_id)
                if not entry:
                    raise CompileError(f"Unknown opcode: {opcode_id}", line=opcode_tok.line, column=opcode_tok.column)
                    
                # Validate arity
                expected = entry.get('operands', [])
                min_operands = 0
                max_operands = 0
                has_variadic = False
                
                for param in expected:
                    if param.startswith('['):
                        max_operands += 1
                    elif param.startswith('...'):
                        has_variadic = True
                        max_operands = float('inf')
                    else:
                        min_operands += 1
                        max_operands += 1
                        
                if len(operands) < min_operands or len(operands) > max_operands:
                    raise CompileError(f"Opcode {opcode_id} expects {min_operands} to {max_operands} operands, got {len(operands)}", 
                                       line=opcode_tok.line, column=opcode_tok.column)
                                       
                instructions.append(Instruction(opcode_id, operands, opcode_tok.line, opcode_tok.column, entry))
                current_group.clear()
            else:
                current_group.append(tok)
                
        if current_group:
            tok = current_group[-1]
            raise CompileError("Program does not end with 0 terminator", line=tok.line, column=tok.column)
            
        return instructions
