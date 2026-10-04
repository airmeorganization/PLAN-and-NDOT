from typing import List
from ndot.validator import Instruction

class PythonBackend:
    def __init__(self):
        self.code_lines = []
        self.indent_level = 0
        
    def add_line(self, line: str):
        if line.strip():
            self.code_lines.append("    " * self.indent_level + line)
        else:
            self.code_lines.append("")
            
    def generate(self, instructions: List[Instruction]) -> str:
        self.add_line("from ndot import ndot_runtime as rt")
        self.add_line("")
        
        for inst in instructions:
            entry = inst.registry_entry
            template = entry.get('python', '')
            
            if not template:
                # If there's no template but it's an end block, we just dedent
                if entry.get('closes_block'):
                    self.indent_level = max(0, self.indent_level - 1)
                continue
                
            # Process operands
            kwargs = {}
            op_specs = entry.get('operands', [])
            op_idx = 0
            
            for spec in op_specs:
                is_variadic = spec.startswith('...')
                is_optional = spec.startswith('[')
                
                # Extract the name (e.g. S:a -> a, D:dest -> dest)
                clean_spec = spec.strip('.[]')
                parts = clean_spec.split(':')
                kind = parts[0]
                name = parts[1] if len(parts) > 1 else 'val'
                
                if is_variadic:
                    vals = inst.operands[op_idx:]
                    if kind == 'L':
                        kwargs[name] = ", ".join(vals)
                    elif kind == 'S':
                        kwargs[name] = ", ".join(f"s{v}" for v in vals)
                    break # variadic is always last
                else:
                    if op_idx < len(inst.operands):
                        val = inst.operands[op_idx]
                        if kind == 'S' or kind == 'D':
                            kwargs[name] = f"s{val}"
                        elif kind == 'F':
                            kwargs[name] = val
                        else: # L or C
                            kwargs[name] = val
                    else:
                        kwargs[name] = "" # Optional missing
                    op_idx += 1
                    
            if entry.get('closes_block'):
                self.indent_level = max(0, self.indent_level - 1)
                
            line = template.format(**kwargs)
            self.add_line(line)
            
            if entry.get('opens_block'):
                self.indent_level += 1
                
        return "\n".join(self.code_lines) + "\n"
