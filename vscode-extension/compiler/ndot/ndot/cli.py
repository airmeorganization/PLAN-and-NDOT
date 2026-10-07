import sys
import os
import json
import argparse

# Ensure parent directory is in sys.path so 'ndot' and 'common' packages are always resolvable
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from ndot.lexer import Lexer
from ndot.registry import Registry
from ndot.validator import Validator
from ndot.python_backend import PythonBackend
from ndot.disasm import disassemble, assemble
from common.diagnostics import CompileError

def main():
    parser = argparse.ArgumentParser(description="N-DOT toolchain")
    parser.add_argument("command", choices=["run", "build", "check", "dis", "asm"])
    parser.add_argument("file", help="Input file (.ndot or .ndasm)")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("--allow-files", action="store_true", help="Allow file operations (803, 805, 406, 102, 106)")
    parser.add_argument("--allow-network", action="store_true", help="Allow network fetch operations (804)")
    parser.add_argument("--json", action="store_true", help="Output structured diagnostics as JSON")

    args = parser.parse_args()
    registry = Registry()

    try:
        if args.command == "asm":
            with open(args.file, 'r', encoding='utf-8') as f:
                ndasm_source = f.read()
            numeric_code = assemble(ndasm_source, registry)
            out_file = args.output or args.file.replace(".ndasm", ".ndot")
            with open(out_file, 'w', encoding='ascii') as f:
                f.write(numeric_code)
            print(f"Assembled {out_file}")
            return

        with open(args.file, 'r', encoding='ascii') as f:
            source = f.read()

        lexer = Lexer(source)
        tokens = lexer.tokenize()

        validator = Validator(registry)
        instructions = validator.validate(tokens)

        if args.command == "check":
            if args.json:
                print(json.dumps({"ok": True, "diagnostics": []}))
            else:
                print("Check passed.")
            return

        if args.command == "dis":
            listing = disassemble(instructions)
            print(listing)
            return

        backend = PythonBackend()
        python_code = backend.generate(instructions)

        if args.command == "build":
            out_file = args.output or args.file.replace(".ndot", ".py")
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"Built {out_file}")

        elif args.command == "run":
            from ndot import ndot_runtime as rt
            rt.set_permissions(allow_files=args.allow_files, allow_network=args.allow_network)
            exec_globals = {
                "__name__": "__main__",
                "__builtins__": __builtins__,
                "rt": rt,
            }
            try:
                exec(python_code, exec_globals)
            except RuntimeError as err:
                if "N303" in str(err):
                    print(f"Runtime Error: {err}")
                    sys.exit(1)
                raise

    except CompileError as e:
        if args.json:
            print(json.dumps(e.to_dict()))
        else:
            print(f"Compile Error: {e}")
        sys.exit(1)
    except Exception as e:
        if args.json:
            print(json.dumps({
                "ok": False,
                "diagnostics": [{
                    "code": "N999",
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
