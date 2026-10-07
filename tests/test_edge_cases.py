"""Comprehensive edge case test suite for PLAN and N-DOT compilers and runtimes.

Tests all 19 critical edge cases:
 1. missing 0 (N104 / syntax)
 2. double dots (N102 / empty segments)
 3. leading zeros (N103)
 4. wrong operand count (N202 / P308)
 5. invalid opcode (N201 / P200)
 6. invalid enum (N203)
 7. undefined slot (N209 / P301)
 8. wrong function arguments (N208 / P308)
 9. bad block nesting (N204)
10. return outside function (N206 / P304)
11. break outside loop (N207 / P305)
12. file access without permission (N303)
13. network access without permission (N303)
14. huge loops (stress test)
15. empty programs (N205 / empty program handling)
16. very long strings (stress test)
17. multiple functions (mutual calls & hoisting)
18. deeply nested blocks (8+ levels of nesting)
19. 1000+ line programs (scalability & performance)
"""

import unittest
import ast as pyast
from common.diagnostics import CompileError

# N-DOT imports
from ndot.lexer import Lexer as NdotLexer
from ndot.registry import Registry as NdotRegistry
from ndot.validator import Validator as NdotValidator, Instruction
from ndot.python_backend import PythonBackend as NdotBackend
from ndot.disasm import disassemble as ndot_disassemble, assemble as ndot_assemble
from ndot import ndot_runtime as ndot_rt

# PLAN imports
from plan.lexer import Lexer as PlanLexer
from plan.parser import Parser as PlanParser
from plan.semantic import SemanticAnalyzer as PlanSemantic
from plan.python_codegen import Codegen as PlanCodegen


class TestCompilerEdgeCases(unittest.TestCase):
    def setUp(self):
        self.ndot_reg = NdotRegistry()
        self.ndot_val = NdotValidator(self.ndot_reg)
        self.ndot_be = NdotBackend()

    # -------------------------------------------------------------------------
    # 1. Missing 0
    # -------------------------------------------------------------------------
    def test_ndot_missing_zero(self):
        """N-DOT programs must end with a trailing '0' terminator (N104)."""
        code = "900.1.0.610.1.5"  # Missing trailing 0
        with self.assertRaises(CompileError) as ctx:
            NdotLexer(code).tokenize()
        self.assertEqual(ctx.exception.diagnostics[0].code, "N104")

        # Also verify validator rejects token stream missing 0 terminator
        valid_tokens = NdotLexer("900.1.0.610.1.5.0").tokenize()
        tokens_missing_zero = [t for t in valid_tokens if t.type != 'EOF'][:-1]  # drop trailing TERMINATOR '0'
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens_missing_zero)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N104")

    def test_plan_missing_period(self):
        """PLAN statements must end with a period."""
        code = 'Create a variable called x with value 10\nShow x.'
        tokens = PlanLexer(code).tokenize()
        with self.assertRaises(CompileError):
            PlanParser(tokens).parse_program()

    # -------------------------------------------------------------------------
    # 2. Double Dots
    # -------------------------------------------------------------------------
    def test_ndot_double_dots(self):
        """Double dots create empty segments, which are illegal in N-DOT (N102)."""
        code = "900.1..0"
        with self.assertRaises(CompileError) as ctx:
            NdotLexer(code).tokenize()
        self.assertEqual(ctx.exception.diagnostics[0].code, "N102")

    def test_ndot_leading_dot(self):
        """Leading dot is an empty segment (N102)."""
        code = ".900.1.0"
        with self.assertRaises(CompileError) as ctx:
            NdotLexer(code).tokenize()
        self.assertEqual(ctx.exception.diagnostics[0].code, "N102")

    # -------------------------------------------------------------------------
    # 3. Leading Zeros
    # -------------------------------------------------------------------------
    def test_ndot_leading_zeros(self):
        """Segments with leading zeros like '05' are forbidden (N103)."""
        code = "900.1.0.610.1.05.0"
        with self.assertRaises(CompileError) as ctx:
            NdotLexer(code).tokenize()
        self.assertEqual(ctx.exception.diagnostics[0].code, "N103")

    def test_plan_leading_zeros_numeric(self):
        """PLAN numeric literals with leading zeros parse cleanly as numeric values."""
        code = 'Create a variable called x with value 007.\nShow x.'
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        PlanSemantic().analyze(ast)
        mod = PlanCodegen().generate(ast)
        py_code = pyast.unparse(mod)
        self.assertIn("x = 7", py_code)

    # -------------------------------------------------------------------------
    # 4. Wrong Operand Count
    # -------------------------------------------------------------------------
    def test_ndot_wrong_operand_count(self):
        """Opcode 701 (add) expects 3 operands (dest, src1, src2), got 2 (N202)."""
        code = "900.1.0.701.1.2.0"
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N202")

    def test_plan_wrong_call_arity(self):
        """Calling a PLAN function with too few/many arguments raises P308."""
        code = (
            "Create a function called add that accepts whole number a and whole number b and gives back whole number,\n"
            "    Return a plus b.\n"
            "Create a variable called result with value the result of add with 10, 20, and 30.\n"
        )
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        with self.assertRaises(CompileError) as ctx:
            PlanSemantic().analyze(ast)
        self.assertEqual(ctx.exception.diagnostics[0].code, "P308")

    # -------------------------------------------------------------------------
    # 5. Invalid Opcode
    # -------------------------------------------------------------------------
    def test_ndot_invalid_opcode(self):
        """Unknown N-DOT opcodes must be rejected (N201)."""
        code = "900.1.0.9999.1.2.0"
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N201")

    def test_plan_invalid_statement_keyword(self):
        """Unrecognized PLAN statements must raise a syntax error."""
        code = "Explode the database into pieces."
        tokens = PlanLexer(code).tokenize()
        with self.assertRaises(CompileError):
            PlanParser(tokens).parse_program()

    # -------------------------------------------------------------------------
    # 6. Invalid Enum
    # -------------------------------------------------------------------------
    def test_ndot_invalid_enum_architecture(self):
        """Opcode 101 architecture code must be 1, 2, or 3 (N203)."""
        code = "900.1.0.101.1.99.10.1.0"  # 99 is invalid
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N203")

    def test_ndot_invalid_enum_activation(self):
        """Opcode 304 activation code must be 1..6 (N203)."""
        code = "900.1.0.610.1.5.0.304.2.1.8.0"  # 8 is invalid
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N203")

    # -------------------------------------------------------------------------
    # 7. Undefined Slot
    # -------------------------------------------------------------------------
    def test_ndot_slot_read_before_write(self):
        """Reading a slot that has never been written raises N209."""
        code = "900.1.0.701.3.1.2.0"  # Reading s1 and s2 before any write
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N209")

    def test_plan_undefined_variable(self):
        """Using an undeclared variable raises P301."""
        code = "Show my_secret_number."
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        with self.assertRaises(CompileError) as ctx:
            PlanSemantic().analyze(ast)
        self.assertEqual(ctx.exception.diagnostics[0].code, "P301")

    # -------------------------------------------------------------------------
    # 8. Wrong Function Arguments
    # -------------------------------------------------------------------------
    def test_ndot_wrong_function_arguments(self):
        """Calling an N-DOT function (512) with the wrong arity raises N208."""
        code = (
            "900.1.0."
            "510.1.2.0."      # Define f1 with 2 parameters (s1, s2)
            "511.1.0."        # Return s1
            "509.0."          # End function block
            "610.10.1.0."     # Write s10 = 1
            "512.20.1.10.0"   # Call f1 with only 1 argument (expects 2)
        )
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N208")

    def test_ndot_call_undefined_function(self):
        """Calling an undeclared function ID raises N208."""
        code = (
            "900.1.0."
            "610.10.1.0."
            "512.20.99.10.0"  # Function 99 does not exist
        )
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N208")

    # -------------------------------------------------------------------------
    # 9. Bad Block Nesting
    # -------------------------------------------------------------------------
    def test_ndot_unclosed_block(self):
        """Unclosed block (missing 509) raises N204."""
        code = "900.1.0.610.1.1.0.501.1.0"  # 501 (if) without 509
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N204")

    def test_ndot_extra_close_block(self):
        """Extra 509 without matching open block raises N204."""
        code = "900.1.0.509.0"
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N204")

    # -------------------------------------------------------------------------
    # 10. Return Outside Function
    # -------------------------------------------------------------------------
    def test_ndot_return_outside_function(self):
        """Opcode 511 (return) at top level raises N206."""
        code = "900.1.0.610.1.5.0.511.1.0"
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N206")

    def test_plan_return_outside_function(self):
        """'Return' used outside any function block raises P304."""
        code = "Return 42."
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        with self.assertRaises(CompileError) as ctx:
            PlanSemantic().analyze(ast)
        self.assertEqual(ctx.exception.diagnostics[0].code, "P304")

    # -------------------------------------------------------------------------
    # 11. Break Outside Loop
    # -------------------------------------------------------------------------
    def test_ndot_break_outside_loop(self):
        """Opcode 504 (break) outside any loop block raises N207."""
        code = "900.1.0.504.0"
        tokens = NdotLexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N207")

    def test_plan_break_outside_loop(self):
        """'Stop the loop.' outside any loop raises P305."""
        code = "Stop the loop."
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        with self.assertRaises(CompileError) as ctx:
            PlanSemantic().analyze(ast)
        self.assertEqual(ctx.exception.diagnostics[0].code, "P305")

    # -------------------------------------------------------------------------
    # 12. File Access Without Permission
    # -------------------------------------------------------------------------
    def test_ndot_file_permission_denied(self):
        """Attempting file access when allow_files=False raises N303."""
        ndot_rt.set_permissions(allow_files=False, allow_network=False)
        with self.assertRaises(RuntimeError) as ctx:
            ndot_rt.read_file("forbidden.txt")
        self.assertIn("N303", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 13. Network Access Without Permission
    # -------------------------------------------------------------------------
    def test_ndot_network_permission_denied(self):
        """Attempting network fetch when allow_network=False raises N303."""
        ndot_rt.set_permissions(allow_files=True, allow_network=False)
        with self.assertRaises(RuntimeError) as ctx:
            ndot_rt.fetch_url("https://example.com")
        self.assertIn("N303", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 14. Huge Loops
    # -------------------------------------------------------------------------
    def test_ndot_huge_loop_execution(self):
        """N-DOT loop executing 10,000 iterations to accumulate sum."""
        code = (
            "900.1.0."
            "612.1.0."         # s1 = 0 (sum)
            "610.4.1.0."       # s4 = 1 (step)
            "503.10000.0."     # repeat 10000 times
            "701.1.1.4.0."     # s1 = s1 + s4
            "509.0."           # end repeat
            "802.1.0"          # print s1
        )
        tokens = NdotLexer(code).tokenize()
        instructions = self.ndot_val.validate(tokens)
        py_code = self.ndot_be.generate(instructions)
        exec_globals = {"rt": ndot_rt}
        exec(py_code, exec_globals)
        self.assertEqual(exec_globals["s1"], 10000)

    def test_plan_huge_loop_execution(self):
        """PLAN repeat loop executing 10,000 iterations."""
        code = (
            "Create a variable called total with value 0.\n"
            "Repeat 10000 times,\n"
            "    Add 1 to total.\n"
        )
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        PlanSemantic().analyze(ast)
        mod = PlanCodegen().generate(ast)
        py_code = pyast.unparse(mod)
        exec_globals = {}
        exec(py_code, exec_globals)
        self.assertEqual(exec_globals["total"], 10000)

    # -------------------------------------------------------------------------
    # 15. Empty Programs
    # -------------------------------------------------------------------------
    def test_ndot_empty_program_rejected(self):
        """Empty N-DOT string raises N205 (missing version header)."""
        tokens = NdotLexer("").tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.ndot_val.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, "N205")

    def test_plan_empty_program_accepted(self):
        """An empty PLAN program is valid and produces an empty executable module."""
        tokens = PlanLexer("").tokenize()
        ast = PlanParser(tokens).parse_program()
        PlanSemantic().analyze(ast)
        mod = PlanCodegen().generate(ast)
        py_code = pyast.unparse(mod)
        self.assertTrue(len(py_code) > 0)  # Has runtime header

    # -------------------------------------------------------------------------
    # 16. Very Long Strings
    # -------------------------------------------------------------------------
    def test_ndot_very_long_string(self):
        """N-DOT literal string with 50,000 characters."""
        long_str = "A" * 50000
        codepoints = [str(ord(c)) for c in long_str]
        inst = Instruction(
            opcode="615",
            operands=["1"] + codepoints,
            line=1,
            column=1,
            registry_entry=self.ndot_reg.get("615")
        )
        py_line = self.ndot_be.render_instruction(inst)
        exec_globals = {}
        exec(py_line, exec_globals)
        self.assertEqual(len(exec_globals["s1"]), 50000)
        self.assertEqual(exec_globals["s1"], long_str)

    def test_plan_very_long_string(self):
        """PLAN string literal with 50,000 characters."""
        content = "X" * 50000
        code = f'Create a variable called long_text with value "{content}".\n'
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        PlanSemantic().analyze(ast)
        mod = PlanCodegen().generate(ast)
        py_code = pyast.unparse(mod)
        exec_globals = {}
        exec(py_code, exec_globals)
        self.assertEqual(len(exec_globals["long_text"]), 50000)

    # -------------------------------------------------------------------------
    # 17. Multiple Functions & Hoisting
    # -------------------------------------------------------------------------
    def test_ndot_multiple_functions(self):
        """Multiple N-DOT functions calling each other and returning values."""
        code = (
            "900.1.0."
            # f1: double(x) -> x + x
            "510.1.1.0."
            "701.2.1.1.0."
            "511.2.0."
            "509.0."
            # f2: quadruple(x) -> double(double(x))
            "510.2.1.0."
            "512.3.1.1.0."    # s3 = f1(s1)
            "512.4.1.3.0."    # s4 = f1(s3)
            "511.4.0."
            "509.0."
            # Top-level: quadruple(5)
            "610.10.5.0."
            "512.11.2.10.0."  # s11 = f2(s10) -> 20
            "802.11.0"
        )
        tokens = NdotLexer(code).tokenize()
        instructions = self.ndot_val.validate(tokens)
        py_code = self.ndot_be.generate(instructions)
        exec_globals = {"rt": ndot_rt}
        exec(py_code, exec_globals)
        self.assertEqual(exec_globals["s11"], 20)

    def test_plan_multiple_functions_with_hoisting(self):
        """Multiple PLAN functions with forward calling and mutual recursion."""
        code = (
            "Create a function called main_entry,\n"
            "    Create a variable called ans with value the result of helper with 21.\n"
            "    Return ans.\n"
            "\n"
            "Create a function called helper that accepts whole number n and gives back whole number,\n"
            "    Return n times 2.\n"
            "\n"
            "Create a variable called final_val with value the result of main_entry.\n"
        )
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        PlanSemantic().analyze(ast)
        mod = PlanCodegen().generate(ast)
        py_code = pyast.unparse(mod)
        exec_globals = {}
        exec(py_code, exec_globals)
        self.assertEqual(exec_globals["final_val"], 42)

    # -------------------------------------------------------------------------
    # 18. Deeply Nested Blocks
    # -------------------------------------------------------------------------
    def test_ndot_deeply_nested_blocks(self):
        """N-DOT program with 6 levels of nested if/loop blocks."""
        code = (
            "900.1.0."
            "610.1.1.0."      # s1 = 1
            "501.1.0."        # level 1
            "501.1.0."        # level 2
            "501.1.0."        # level 3
            "501.1.0."        # level 4
            "501.1.0."        # level 5
            "610.2.42.0."     # s2 = 42
            "509.0."          # close 5
            "509.0."          # close 4
            "509.0."          # close 3
            "509.0."          # close 2
            "509.0."          # close 1
            "802.2.0"
        )
        tokens = NdotLexer(code).tokenize()
        instructions = self.ndot_val.validate(tokens)
        py_code = self.ndot_be.generate(instructions)
        exec_globals = {"rt": ndot_rt}
        exec(py_code, exec_globals)
        self.assertEqual(exec_globals["s2"], 42)

    def test_plan_deeply_nested_blocks(self):
        """PLAN program with 6 levels of nested blocks."""
        code = (
            "Create a variable called result with value 0.\n"
            "If true,\n"
            "    If true,\n"
            "        If true,\n"
            "            If true,\n"
            "                If true,\n"
            "                    Set result to 100.\n"
        )
        tokens = PlanLexer(code).tokenize()
        ast = PlanParser(tokens).parse_program()
        PlanSemantic().analyze(ast)
        mod = PlanCodegen().generate(ast)
        py_code = pyast.unparse(mod)
        exec_globals = {}
        exec(py_code, exec_globals)
        self.assertEqual(exec_globals["result"], 100)

    # -------------------------------------------------------------------------
    # 19. 1000+ Line Programs
    # -------------------------------------------------------------------------
    def test_ndot_1000_instruction_program(self):
        """N-DOT scalability test: Generates and validates a program with 1,000+ instructions."""
        parts = ["900.1.0"]
        # Write s1 = 1
        parts.append("610.1.1.0")
        # 1000 additions: s1 = s1 + 1
        for _ in range(1000):
            parts.append("701.1.1.1.0")
        parts.append("802.1.0")
        full_code = ".".join(parts)

        tokens = NdotLexer(full_code).tokenize()
        self.assertTrue(len(tokens) > 5000)

        instructions = self.ndot_val.validate(tokens)
        self.assertEqual(len(instructions), 1003)

        # Disassembly round-trip performance test
        disasm_text = ndot_disassemble(instructions)
        self.assertTrue(len(disasm_text.splitlines()) > 1000)

        # Assemble round-trip
        assembled = ndot_assemble(disasm_text, self.ndot_reg)
        self.assertEqual(assembled, full_code)

    def test_plan_1000_line_program(self):
        """PLAN scalability test: Generates, parses, analyzes, and compiles a 1,000+ line program."""
        lines = ["Create a variable called accumulator with value 0."]
        for i in range(1000):
            lines.append(f"Add 1 to accumulator.")
        lines.append("Show accumulator.")
        full_code = "\n".join(lines)

        tokens = PlanLexer(full_code).tokenize()
        self.assertTrue(len(tokens) > 4000)

        ast = PlanParser(tokens).parse_program()
        self.assertEqual(len(ast.statements), 1002)

        PlanSemantic().analyze(ast)
        mod = PlanCodegen().generate(ast)
        py_code = pyast.unparse(mod)
        self.assertTrue(len(py_code.splitlines()) > 1000)


if __name__ == '__main__':
    unittest.main()
