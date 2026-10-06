import sys
import os
import argparse
import ast as pyast
from plan.lexer import Lexer
from plan.parser import Parser
from plan.semantic import SemanticAnalyzer
from plan.python_codegen import Codegen
from common.diagnostics import CompileError

def main():
    parser = argparse.ArgumentParser(description="PLAN toolchain")
    parser.add_argument("command", choices=["run", "build", "check", "python"])
    parser.add_argument("file", help="Input file (.plan)")
    parser.add_argument("-o", "--output", help="Output file")
    
    args = parser.parse_args()
    
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            source = f.read()
            
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse_program()
        
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)
        
        if args.command == "check":
            print("Check passed.")
            return
            
        codegen = Codegen()
        python_ast = codegen.generate(ast)
        python_code = pyast.unparse(python_ast)
        
        if args.command == "python":
            print(python_code)
            return
            
        if args.command == "build":
            out_file = args.output or args.file.replace(".plan", ".py")
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"Built {out_file}")
            
        elif args.command == "run":
            # Add current directory to path for rt imports
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            exec(python_code, {})
            
    except CompileError as e:
        print(f"Compile Error: {e.message} at line {e.line}, column {e.column}")
        if e.source_line:
            print(f"  {e.source_line}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
