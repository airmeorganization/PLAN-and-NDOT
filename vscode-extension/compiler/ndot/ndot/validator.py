from typing import List, NamedTuple, Optional, Dict, Set, Tuple
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
    """N-DOT Semantic, Structural, and Dataflow Validator.

    Enforces the full N-DOT validation contract (spec/NDOT.md §7):
    - N104: Program does not end with the terminator 0
    - N105: Empty instruction (0.0)
    - N201: Unknown opcode
    - N202: Wrong number of operands
    - N203: Enum code out of range
    - N204: Unbalanced block structure (missing/extra 509, misplaced 506)
    - N205: Missing or unsupported 900 version header
    - N206: Function placement (511 outside function, 510 nested)
    - N207: Loop context (504/505 outside loop)
    - N208: Undefined function or wrong argument count
    - N209: Slot read before write
    """

    def __init__(self, registry: Registry):
        self.registry = registry

    def _classify_operands(self, entry: dict, operands: List[str]) -> Tuple[List[int], List[int]]:
        """Separates operands into source slots (read) and destination slots (written)."""
        specs = entry.get('operands', [])
        d_slots = []
        s_slots = []

        variadic_spec = None
        for s in specs:
            if s.startswith('...'):
                variadic_spec = s[3:]
                break

        fixed_specs = [s for s in specs if not s.startswith('...')]

        for i, val in enumerate(operands):
            if i < len(fixed_specs):
                spec = fixed_specs[i].strip('[]')
            elif variadic_spec:
                spec = variadic_spec.strip('[]')
            else:
                continue

            clean_kind = spec.split(':')[0]
            try:
                num = int(val)
            except ValueError:
                continue

            if clean_kind == 'D':
                d_slots.append(num)
            elif clean_kind == 'S':
                s_slots.append(num)

        return s_slots, d_slots

    def validate(self, tokens: List[Token]) -> List[Instruction]:
        instructions: List[Instruction] = []
        current_group: List[Token] = []

        # Step 1: Token grouping into instructions & arity check (N105, N201, N202)
        for tok in tokens:
            if tok.type == 'EOF':
                break

            if tok.type == 'TERMINATOR':
                if not current_group:
                    raise CompileError("Empty instruction (0.0)", line=tok.line, column=tok.column, code="N105")

                opcode_tok = current_group[0]
                opcode_id = opcode_tok.value
                operands = [t.value for t in current_group[1:]]

                entry = self.registry.get_opcode(opcode_id)
                if not entry:
                    raise CompileError(f"Unknown opcode: {opcode_id}", line=opcode_tok.line, column=opcode_tok.column, code="N201")

                expected = entry.get('operands', [])
                min_operands = 0
                max_operands = 0

                for param in expected:
                    if param.startswith('['):
                        max_operands += 1
                    elif param.startswith('...'):
                        max_operands = float('inf')
                    else:
                        min_operands += 1
                        max_operands += 1

                if len(operands) < min_operands or len(operands) > max_operands:
                    arity_desc = f"{min_operands}" if min_operands == max_operands else f"{min_operands} to {max_operands}"
                    raise CompileError(
                        f"Opcode {opcode_id} ({entry.get('name', '')}) expects {arity_desc} operands, got {len(operands)}",
                        line=opcode_tok.line,
                        column=opcode_tok.column,
                        code="N202"
                    )

                instructions.append(Instruction(opcode_id, operands, opcode_tok.line, opcode_tok.column, entry))
                current_group.clear()
            else:
                current_group.append(tok)

        if current_group:
            tok = current_group[-1]
            raise CompileError("Program does not end with the terminator '0'", line=tok.line, column=tok.column, code="N104")

        # Step 2: N205 Version Header Check
        if not instructions:
            raise CompileError("Missing 900 version header: program is empty", line=1, column=1, code="N205")

        first_inst = instructions[0]
        if first_inst.opcode != "900":
            raise CompileError(
                "Missing 900 version header: programs must begin with 900.1.0",
                line=first_inst.line,
                column=first_inst.column,
                code="N205"
            )

        if not first_inst.operands or first_inst.operands[0] != "1":
            major = first_inst.operands[0] if first_inst.operands else "missing"
            raise CompileError(
                f"Unsupported N-DOT version: {major} (expected 1)",
                line=first_inst.line,
                column=first_inst.column,
                code="N205"
            )

        for inst in instructions[1:]:
            if inst.opcode == "900":
                raise CompileError(
                    "Misplaced 900 version header: version can only appear once at the start of the program",
                    line=inst.line,
                    column=inst.column,
                    code="N205"
                )

        # Step 3: N203 Enum Validation
        for inst in instructions:
            if inst.opcode == "101":
                arch = int(inst.operands[1])
                if arch not in (1, 2, 3):
                    raise CompileError(
                        f"Architecture code {arch} out of range for opcode 101 (expected 1: linear, 2: logistic, 3: mlp)",
                        line=inst.line,
                        column=inst.column,
                        code="N203"
                    )
            elif inst.opcode == "304":
                kind = int(inst.operands[2])
                if kind not in (1, 2, 3, 4, 5, 6):
                    raise CompileError(
                        f"Activation code {kind} out of range for opcode 304 (expected 1..6: relu, sigmoid, tanh, softmax, gelu, identity)",
                        line=inst.line,
                        column=inst.column,
                        code="N203"
                    )
            elif inst.opcode == "307":
                kind = int(inst.operands[3])
                if kind not in (1, 2, 3):
                    raise CompileError(
                        f"Loss code {kind} out of range for opcode 307 (expected 1: mse, 2: cross-entropy, 3: binary cross-entropy)",
                        line=inst.line,
                        column=inst.column,
                        code="N203"
                    )

        # Step 4: Pre-scan Function Declarations for N208
        declared_functions: Dict[str, int] = {}
        for inst in instructions:
            if inst.opcode == "510":
                fn_id = inst.operands[0]
                param_count = int(inst.operands[1]) if len(inst.operands) > 1 else 0
                if fn_id in declared_functions:
                    raise CompileError(
                        f"Duplicate function definition for function id {fn_id}",
                        line=inst.line,
                        column=inst.column,
                        code="N208"
                    )
                declared_functions[fn_id] = param_count

        # Step 5: Structural & Context Checks (N204, N206, N207, N208) + Dataflow (N209)
        block_stack: List[dict] = []
        top_level_slots: Set[int] = set()
        function_slots: Dict[str, Set[int]] = {}
        current_func_id: Optional[str] = None

        loop_opcodes = {"502", "503", "507", "508"}

        for inst in instructions:
            opcode = inst.opcode
            active_slots = function_slots[current_func_id] if current_func_id is not None else top_level_slots

            # Check 510 nesting (N206)
            if opcode == "510":
                if len(block_stack) > 0:
                    raise CompileError(
                        "Nested 510: functions cannot be nested inside blocks in N-DOT v0.1",
                        line=inst.line,
                        column=inst.column,
                        code="N206"
                    )
                fn_id = inst.operands[0]
                param_count = declared_functions[fn_id]
                current_func_id = fn_id
                function_slots[fn_id] = set(range(1, param_count + 1))
                block_stack.append({
                    "opcode": "510",
                    "line": inst.line,
                    "column": inst.column,
                    "has_else": False,
                    "is_loop": False,
                    "is_function": True,
                    "func_id": fn_id
                })
                continue

            # Check 511 return context (N206)
            if opcode == "511":
                if not any(b["is_function"] for b in block_stack):
                    raise CompileError(
                        "511 (return) cannot appear outside a function",
                        line=inst.line,
                        column=inst.column,
                        code="N206"
                    )

            # Check 504 / 505 loop context (N207)
            if opcode in ("504", "505"):
                if not any(b["is_loop"] for b in block_stack):
                    op_name = "504 (stop)" if opcode == "504" else "505 (next)"
                    raise CompileError(
                        f"{op_name} cannot appear outside a loop",
                        line=inst.line,
                        column=inst.column,
                        code="N207"
                    )

            # Check 506 otherwise / else context (N204)
            if opcode == "506":
                if not block_stack or block_stack[-1]["opcode"] != "501":
                    raise CompileError(
                        "Misplaced 506: 'otherwise' can only appear directly inside an 'if' (501) block",
                        line=inst.line,
                        column=inst.column,
                        code="N204"
                    )
                if block_stack[-1]["has_else"]:
                    raise CompileError(
                        "Duplicate 506 inside the same 'if' block",
                        line=inst.line,
                        column=inst.column,
                        code="N204"
                    )
                block_stack[-1]["has_else"] = True
                continue

            # Check block opens
            if opcode in ("501", "502", "503", "507", "508"):
                block_stack.append({
                    "opcode": opcode,
                    "line": inst.line,
                    "column": inst.column,
                    "has_else": False,
                    "is_loop": opcode in loop_opcodes,
                    "is_function": False,
                    "func_id": None
                })

            # Check 509 end block (N204)
            if opcode == "509":
                if not block_stack:
                    raise CompileError(
                        "Unbalanced block: unexpected 509 with no open block to end",
                        line=inst.line,
                        column=inst.column,
                        code="N204"
                    )
                popped = block_stack.pop()
                if popped["is_function"]:
                    current_func_id = None
                continue

            # Check 512 function call (N208)
            if opcode == "512":
                call_fn_id = inst.operands[1]
                args = inst.operands[2:]
                if call_fn_id not in declared_functions:
                    raise CompileError(
                        f"Call to undefined function id {call_fn_id}",
                        line=inst.line,
                        column=inst.column,
                        code="N208"
                    )
                expected_params = declared_functions[call_fn_id]
                if len(args) != expected_params:
                    raise CompileError(
                        f"Function {call_fn_id} expects {expected_params} arguments, got {len(args)}",
                        line=inst.line,
                        column=inst.column,
                        code="N208"
                    )

            # Dataflow: N209 Slot read before write
            s_slots, d_slots = self._classify_operands(inst.registry_entry, inst.operands)

            for s in s_slots:
                if s <= 0:
                    raise CompileError(
                        f"Invalid slot number s{s}: slots must be >= 1",
                        line=inst.line,
                        column=inst.column,
                        code="N209"
                    )
                if s not in active_slots:
                    raise CompileError(
                        f"Slot s{s} read before write",
                        line=inst.line,
                        column=inst.column,
                        code="N209"
                    )

            for d in d_slots:
                if d <= 0:
                    raise CompileError(
                        f"Invalid destination slot number s{d}: slots must be >= 1",
                        line=inst.line,
                        column=inst.column,
                        code="N209"
                    )
                active_slots.add(d)

        # End of program block check (N204)
        if block_stack:
            unclosed = block_stack[-1]
            raise CompileError(
                f"Unbalanced block: expected 509 to close opcode {unclosed['opcode']} opened at line {unclosed['line']}",
                line=unclosed["line"],
                column=unclosed["column"],
                code="N204"
            )

        return instructions
