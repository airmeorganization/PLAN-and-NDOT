# Future Updates

Both PLAN and N-DOT have been updated so that they theoretically cover **100% of Python's syntax and capabilities**, meaning you can build anything with them just like Python.

However, moving forward, the following areas will be expanded in upcoming revisions:

### 1. Extending the PLAN Parser (v0.2)
While the **specifications** now contain the complete syntax for mapping Python's advanced features natively into PLAN (such as OOP, exceptions, async, comprehensions, decorators, and lambdas), the v0.1 parser currently relies on the **`python:` escape hatch** block to implement them.

Future updates will build out the `plan/parser.py` recursive descent engine to parse all of these native blocks directly without needing the escape hatch:
- Native parsing of `Describe a kind of thing...` (Classes)
- Native parsing of `Try... On failure...` (Exceptions)
- Native parsing of `With...` (Context Managers)
- Native parsing of `Decorate with...` (Decorators)
- Native list comprehensions (`a list of ... for every ... when ...`)

### 2. Expanding the N-DOT Registry (v0.2)
The core N-DOT opcode space has been officially updated in the spec and the `registry.json` database to include opcodes for object-oriented programming (52x, 63x), exceptions (53x), and async execution (54x, 55x). 

Future updates will expand the `ndot_runtime.py` capabilities to include:
- Native Tensor graph operations (adding to the 2xx series)
- Advanced loss functions (307 codes)
- Complex neural network layers like transformers (adding to the 3xx series).
- Support for `903` extensions loading external opcode JSON registries.

### 3. Optimizer and Target Lowering (v0.3)
- Building the **Optimizer (v0.2)** for N-DOT to perform constant folding and dead-slot elimination.
- Enabling `plan build --target ndot` (v0.3), allowing PLAN source files to compile directly into N-DOT instruction streams instead of Python AST. This will unify both languages into a single execution intermediate representation.
