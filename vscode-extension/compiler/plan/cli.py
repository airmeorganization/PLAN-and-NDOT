import sys
import os
import json
import argparse
import ast as pyast

# Ensure parent directory is in sys.path so 'plan' and 'common' packages are always resolvable
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

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
    parser.add_argument("--allow-python", action="store_true", help="Allow raw Python lines in PLAN")
    parser.add_argument("--allow-all-modules", action="store_true", help="Lift standard library import restriction")
    parser.add_argument("--json", action="store_true", help="Output structured diagnostics as JSON")
    
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
            if args.json:
                print(json.dumps({"ok": True, "diagnostics": []}))
            else:
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
            exec_globals = {
                "__name__": "__main__",
                "__builtins__": __builtins__,
            }
            exec(python_code, exec_globals)
            
    except CompileError as e:
        if args.json:
            print(json.dumps(e.to_dict()))
        else:
            print(f"Compile Error: {e.message} at line {e.line}, column {e.column}")
            if e.source_line:
                print(f"  {e.source_line}")
        sys.exit(1)
    except Exception as e:
        if args.json:
            print(json.dumps({
                "ok": False,
                "diagnostics": [{
                    "code": "P999",
                    "message": str(e),
                    "line": 1,
                    "column": 1,
                    "severity": "error"
                }]
            }))
        else:
            print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
