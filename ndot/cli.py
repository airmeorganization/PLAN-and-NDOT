import sys
import os
import argparse
from ndot.lexer import Lexer
from ndot.registry import Registry
from ndot.validator import Validator
from ndot.python_backend import PythonBackend
from common.diagnostics import CompileError

def main():
    parser = argparse.ArgumentParser(description="N-DOT toolchain")
    parser.add_argument("command", choices=["run", "build", "check", "dis", "asm"])
    parser.add_argument("file", help="Input file (.ndot)")
    parser.add_argument("-o", "--output", help="Output file")
    
    args = parser.parse_args()
    
    try:
        with open(args.file, 'r', encoding='ascii') as f:
            source = f.read()
            
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        registry = Registry()
        validator = Validator(registry)
        instructions = validator.validate(tokens)
        
        if args.command == "check":
            print("Check passed.")
            return
            
        backend = PythonBackend()
        python_code = backend.generate(instructions)
        
        if args.command == "build":
            out_file = args.output or args.file.replace(".ndot", ".py")
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
