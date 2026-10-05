# Future Updates Roadmap

### Current Status (v0.1 Engine Completed)

The codebase has now bridged the gap from initial prototype to a fully functional language implementation matching the specifications in `spec/PLAN.md` and `spec/NDOT.md`:

1. **PLAN (`plan/`):**
   - **Recursive Descent Parser:** Fully parses native controlled-English grammar without escape hatches.
   - **Full Language Features:**
     - Declarations & Variables (`Create a variable...`, `Let... be...`, `Set... to...`)
     - In-place modifications (`Increase... by...`, `Decrease... by...`, `Add... to...`, `Append... to...`, `Remove... from...`)
     - Conditionals (`When...`, `Otherwise when...`, `Otherwise...`)
     - Loops (`For every X in Y...`, `For every X from A to B [in steps of S]...`, `While...`, `Repeat N times...`)
     - Functions (`Create a function called F that accepts... and gives back...`, hoisted defs, returns)
     - Collections (1-based indexed lists, dictionaries)
     - Phrase Library (`square root of`, `the average of`, `x rounded to n places`, etc. with auto-imports)
     - Error handling (`Try... On failure...`)
     - Input/Output (`Show...`, `Ask... and store the answer in...`)
     - Module imports (`Use the X module...`, `Use A and B from the C module...`)
   - **Python Codegen:** Emits standard Python AST preserving source line numbers.
   - **Toolchain:** `plan run`, `plan build`, `plan check`, `plan python`.

2. **N-DOT (`ndot/`):**
   - **Normative Opcode Registry:** All core opcodes (100–999) across 9 domains (Models, Tensors, Neural ops, Datasets, Control, Memory, Math, I/O, System).
   - **Pure-Python Runtime (`ndot_runtime`):**
     - N-dimensional `Tensor` with broadcasting, matrix multiplication, transpositions, L2 normalization, zeros, ones, randn.
     - Neural operations: Linear layers, Conv1D, Attention (scaled dot-product), Activations (ReLU, Sigmoid, Tanh, Softmax, GELU, Identity), Loss functions (MSE, Cross-entropy, Binary cross-entropy), Layer norm, Embeddings.
     - Datasets: Batching, Shuffling, Train/test splitting, CSV loading.
     - Models: Linear regression, Logistic regression, Multi-Layer Perceptrons with train/fit (gradient descent), predict, evaluate, save/load.
   - **Toolchain:** `ndot run`, `ndot build`, `ndot check`, `ndot dis` (disassembler), `ndot asm` (assembler).

---

### Planned for v0.2

1. **PLAN Classes & Async:**
   - Native parsing of `Describe a kind of thing called <Name>` (OOP classes with fields and methods).
   - Native async functions and tasks (`Asynchronous function...`, `Wait for...`).
   - Direct PLAN calling of N-DOT programs (`Run the N-DOT program "model.ndot" with input x and store in y.`).

2. **N-DOT Optimizer:**
   - Constant folding pass over instruction IR (pre-computing static math and literal operations).
   - Dead-slot elimination (tracking slot read-after-write liveness).
   - Extension registries loading via opcode `903`.

---

### Planned for v0.3

1. **PLAN to N-DOT Target Lowering:**
   - `plan build --target ndot`: Compile PLAN source directly to N-DOT instruction streams.
   - Unifies human-authored PLAN with AI-generated N-DOT.

2. **High-Performance Acceleration Backends:**
   - Optional NumPy, PyTorch, and ONNX backends behind the same N-DOT opcodes.
