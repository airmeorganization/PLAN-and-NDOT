"""Disassembler and Assembler for N-DOT (spec/NDOT.md §9).

Provides:
- disassemble(instructions) -> str: format instructions into readable table
- assemble(text) -> str: convert mnemonic listing back to numeric .ndot format
"""
import re
from typing import List
from ndot.validator import Instruction
from ndot.registry import Registry

def disassemble(instructions: List[Instruction]) -> str:
    lines = [f"{'#':<4} {'op':<5} {'mnemonic':<16} {'operands'}"]
    for idx, inst in enumerate(instructions, 1):
        opcode = inst.opcode
        entry = inst.registry_entry
        mnemonic = entry.get('name', 'unknown').replace(' ', '_')

        operands_str = ""
        if opcode == "615": # text literal
            dest = f"s{inst.operands[0]}"
            text = "".join(chr(int(c)) for c in inst.operands[1:])
            operands_str = f"{dest} {repr(text)}"
        else:
            op_specs = entry.get('operands', [])
            formatted_ops = []
            for i, val in enumerate(inst.operands):
                spec = op_specs[i] if i < len(op_specs) else (op_specs[-1] if op_specs and op_specs[-1].startswith('...') else '')
                if ':dest' in spec or spec.startswith('D') or spec.startswith('S') or spec.startswith('...S'):
                    formatted_ops.append(f"s{val}")
                elif spec.startswith('F'):
                    formatted_ops.append(f"f{val}")
                else:
                    formatted_ops.append(val)
            operands_str = " ".join(formatted_ops)

        lines.append(f"{idx:<4} {opcode:<5} {mnemonic:<16} {operands_str}")
    return "\n".join(lines) + "\n"

def assemble(ndasm_text: str, registry: Registry) -> str:
    """Assembles a mnemonic listing (.ndasm) into numeric N-DOT string."""
    name_to_opcode = {}
    for op, data in registry.opcodes.items():
        m_name = data.get('name', '').replace(' ', '_').lower()
        name_to_opcode[m_name] = op
        name_to_opcode[op] = op

    instructions = []
    for line in ndasm_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = line.split()
        # Header or line format: either [idx, op, mnemonic, ...ops] or [mnemonic, ...ops]
        if parts[0].isdigit():
            if len(parts) >= 3 and parts[1].isdigit():
                op = parts[1]
                ops = parts[3:]
            elif parts[0] in registry.opcodes:
                op = parts[0]
                if len(parts) > 1 and parts[1].lower() in name_to_opcode:
                    ops = parts[2:]
                else:
                    ops = parts[1:]
            else:
                continue
        elif parts[0].lower() in name_to_opcode:
            op = name_to_opcode[parts[0].lower()]
            ops = parts[1:]
        else:
            continue

        # Convert operands
        numeric_ops = []
        if op == "615": # text: sD "Hello"
            dest = ops[0].lstrip('sSdD')
            numeric_ops.append(dest)
            quote_match = re.search(r'["\'](.*)["\']', line)
            text_val = quote_match.group(1) if quote_match else ""
            for ch in text_val:
                numeric_ops.append(str(ord(ch)))
        else:
            for arg in ops:
                clean = arg.lstrip('sSfFdD')
                if clean.isdigit():
                    numeric_ops.append(clean)

        inst_str = ".".join([op] + numeric_ops + ["0"])
        instructions.append(inst_str)

    return ".".join(instructions)
