import unittest
import ast as pyast
from plan.lexer import Lexer
from plan.parser import Parser
from plan.semantic import SemanticAnalyzer
from plan.python_codegen import Codegen
from common.diagnostics import CompileError

class TestPlanCompiler(unittest.TestCase):
    def test_lexer_basic(self):
        code = 'Create a variable called count with value 1.\nShow count.'
        tokens = Lexer(code).tokenize()
        self.assertTrue(len(tokens) > 5)

    def test_parser_basic(self):
        code = 'Create a variable called total with value 10.\nShow total.'
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse_program()
        self.assertEqual(len(ast.statements), 2)

    def test_semantic_success(self):
        code = 'Create a variable called x with value 5.\nShow x.'
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse_program()
        SemanticAnalyzer().analyze(ast)

    def test_semantic_undefined_var(self):
        code = 'Show unknown_var.'
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse_program()
        with self.assertRaises(CompileError) as ctx:
            SemanticAnalyzer().analyze(ast)
        self.assertEqual(ctx.exception.diagnostics[0].code, 'P301')

    def test_semantic_redeclaration(self):
        code = 'Create a variable called x with value 1.\nCreate a variable called x with value 2.'
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse_program()
        with self.assertRaises(CompileError) as ctx:
            SemanticAnalyzer().analyze(ast)
        self.assertEqual(ctx.exception.diagnostics[0].code, 'P302')

    def test_descending_range_codegen(self):
        code = 'For every n from 10 to 1 in steps of -1,\n    Show n.\n'
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse_program()
        mod = Codegen().generate(ast)
        py_code = pyast.unparse(mod)
        self.assertIn('range(10, 1 - 1, -1)', py_code)

    def test_type_annotations_codegen(self):
        code = 'Create a function called calc that accepts number x and whole number y and gives back flag,\n    Return true.\n'
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse_program()
        mod = Codegen().generate(ast)
        py_code = pyast.unparse(mod)
        self.assertIn('def calc(x: float, y: int) -> bool:', py_code)

    def test_ask_and_try_codegen(self):
        code = (
            'Create a variable called total with value 0.\n'
            'Repeat 3 times,\n'
            '    Try,\n'
            '        Ask for a number with "Enter a number: " and store the answer in n.\n'
            '        Add n to total.\n'
            '    On failure,\n'
            '        show "That was not a number, skipping.".\n'
            'Show "Total: " followed by total.\n'
        )
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse_program()
        SemanticAnalyzer().analyze(ast)
        mod = Codegen().generate(ast)
        py_code = pyast.unparse(mod)
        self.assertIn("plan_rt.to_number(input('Enter a number: '))", py_code)
        self.assertIn("print('That was not a number, skipping.')", py_code)
        self.assertIn("total += n", py_code)

if __name__ == '__main__':
    unittest.main()
