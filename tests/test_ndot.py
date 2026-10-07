import unittest
from ndot.lexer import Lexer
from ndot.registry import Registry
from ndot.validator import Validator
from ndot.disasm import disassemble, assemble
from ndot import ndot_runtime as rt
from common.diagnostics import CompileError

class TestNdotToolchain(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()
        self.validator = Validator(self.registry)

    def test_lexer_valid(self):
        code = '900.1.0.610.1.5.0.802.1.0\n'
        tokens = Lexer(code).tokenize()
        self.assertEqual(len(tokens), 11)
        self.assertEqual(tokens[-2].type, 'TERMINATOR')

    def test_lexer_trailing_newline_no_false_dot(self):
        code = '900.1.0.610.1.5.0.802.1.0\r\n'
        tokens = Lexer(code).tokenize()
        instructions = self.validator.validate(tokens)
        self.assertEqual(len(instructions), 3)

    def test_lexer_trailing_dot_error(self):
        code = '900.1.0.\n'
        with self.assertRaises(CompileError) as ctx:
            Lexer(code).tokenize()
        self.assertEqual(ctx.exception.diagnostics[0].code, 'N102')

    def test_validator_missing_version(self):
        code = '610.1.5.0'
        tokens = Lexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.validator.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, 'N205')

    def test_validator_unbalanced_block(self):
        code = '900.1.0.610.1.1.0.501.1.0'
        tokens = Lexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.validator.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, 'N204')

    def test_validator_slot_read_before_write(self):
        code = '900.1.0.701.3.1.2.0'
        tokens = Lexer(code).tokenize()
        with self.assertRaises(CompileError) as ctx:
            self.validator.validate(tokens)
        self.assertEqual(ctx.exception.diagnostics[0].code, 'N209')

    def test_runtime_permission_denied(self):
        rt.set_permissions(allow_files=False, allow_network=False)
        with self.assertRaises(RuntimeError) as ctx:
            rt.read_file('dummy.txt')
        self.assertIn('N303', str(ctx.exception))

    def test_disasm_and_asm_roundtrip(self):
        code = '900.1.0.610.1.7.0.802.1.0'
        tokens = Lexer(code).tokenize()
        instructions = self.validator.validate(tokens)
        listing = disassemble(instructions)
        self.assertIn('positive_integer', listing)
        assembled = assemble(listing, self.registry)
        self.assertEqual(assembled, code)

if __name__ == '__main__':
    unittest.main()
