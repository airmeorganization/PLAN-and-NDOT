from typing import List, Dict, Any
from ndot.validator import Instruction

class PythonBackend:
    """N-DOT to Python Code Generator."""

    def __init__(self):
        self.functions_code: List[str] = []
        self.top_level_code: List[str] = []
        self.indent_level = 0
        self.in_function = False

    def emit_line(self, line: str, target_list: List[str]):
        if line.strip():
            target_list.append("    " * self.indent_level + line)
        else:
            target_list.append("")

    def generate(self, instructions: List[Instruction]) -> str:
        self.functions_code = []
        self.top_level_code = []
        self.indent_level = 0
        self.in_function = False

        # First pass / scan to process instructions
        i = 0
        while i < len(instructions):
            inst = instructions[i]
            entry = inst.registry_entry
            opcode = inst.opcode

            # Handle 510: define function (collect the whole function block)
            if opcode == "510":
                fn_id = inst.operands[0]
                param_count = int(inst.operands[1]) if len(inst.operands) > 1 else 0
                params = ", ".join(f"s{p}" for p in range(1, param_count + 1))
                
                self.functions_code.append(f"def f{fn_id}({params}):")
                self.indent_level = 1
                i += 1
                # Process instructions until matching 509 end block
                fn_block_depth = 1
                while i < len(instructions) and fn_block_depth > 0:
                    inner_inst = instructions[i]
                    inner_entry = inner_inst.registry_entry
                    
                    if inner_entry.get('closes_block'):
                        self.indent_level = max(0, self.indent_level - 1)
                        fn_block_depth -= 1
                        if fn_block_depth == 0:
                            i += 1
                            break

                    line = self.render_instruction(inner_inst)
                    if line:
                        self.emit_line(line, self.functions_code)

                    if inner_entry.get('opens_block'):
                        self.indent_level += 1
                        fn_block_depth += 1

                    i += 1

                self.functions_code.append("")
                self.indent_level = 0
                continue

            # Top-level instructions
            if entry.get('closes_block'):
                self.indent_level = max(0, self.indent_level - 1)

            line = self.render_instruction(inst)
            if line:
                self.emit_line(line, self.top_level_code)

            if entry.get('opens_block'):
                self.indent_level += 1

            i += 1

        output = ["from ndot import ndot_runtime as rt", ""]
        if self.functions_code:
            output.extend(self.functions_code)
        if self.top_level_code:
            output.extend(self.top_level_code)

        return "\n".join(output) + "\n"

    def render_instruction(self, inst: Instruction) -> str:
        entry = inst.registry_entry
        opcode = inst.opcode
        template = entry.get('python', '')

        # 900: version header
        if opcode == "900":
            return ""

        # 509: end block handled by indentation
        if opcode == "509":
            return ""

        # Special lowering for literals
        if opcode == "615": # text
            dest = f"s{inst.operands[0]}"
            codepoints = inst.operands[1:]
            decoded = "".join(chr(int(c)) for c in codepoints)
            return f"{dest} = {repr(decoded)}"

        if opcode == "610": # positive integer
            dest = f"s{inst.operands[0]}"
            val = inst.operands[1]
            return f"{dest} = {val}"

        if opcode == "611": # negative integer
            dest = f"s{inst.operands[0]}"
            val = inst.operands[1]
            return f"{dest} = -{val}"

        if opcode == "612": # zero
            dest = f"s{inst.operands[0]}"
            return f"{dest} = 0"

        if opcode == "613": # positive decimal
            dest = f"s{inst.operands[0]}"
            mantissa = inst.operands[1]
            scale = inst.operands[2]
            return f"{dest} = {mantissa} / (10 ** {scale})"

        if opcode == "614": # negative decimal
            dest = f"s{inst.operands[0]}"
            mantissa = inst.operands[1]
            scale = inst.operands[2]
            return f"{dest} = -({mantissa} / (10 ** {scale}))"

        if opcode == "616": # true
            return f"s{inst.operands[0]} = True"

        if opcode == "617": # false
            return f"s{inst.operands[0]} = False"

        if opcode == "618": # nothing
            return f"s{inst.operands[0]} = None"

        if opcode == "511": # return
            if not inst.operands:
                return "return None"
            return f"return s{inst.operands[0]}"

        # General template substitution
        kwargs = {}
        op_specs = entry.get('operands', [])
        op_idx = 0

        for spec in op_specs:
            is_variadic = spec.startswith('...')
            clean = spec.strip('.[]')
            parts = clean.split(':')
            kind = parts[0]
            name = parts[1] if len(parts) > 1 else 'val'

            if is_variadic:
                vals = inst.operands[op_idx:]
                if kind == 'S':
                    kwargs[name] = ", ".join(f"s{v}" for v in vals)
                elif kind == 'L':
                    kwargs[name] = ", ".join(vals)
                else:
                    kwargs[name] = ", ".join(vals)
                break
            else:
                if op_idx < len(inst.operands):
                    v = inst.operands[op_idx]
                    if kind in ('S', 'D'):
                        kwargs[name] = f"s{v}"
                    else:
                        kwargs[name] = v
                else:
                    kwargs[name] = ""
                op_idx += 1

        return template.format(**kwargs)
