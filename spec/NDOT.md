  # N-DOT Language Specification — v0.1 (draft)

N-DOT is a machine-oriented language for AI workloads. Its source code uses **only eleven characters**:

```text
0 1 2 3 4 5 6 7 8 9 .
```

There are no letters, no whitespace, and no newlines. A complete program looks like this:

```text
900.1.0.615.1.72.101.108.108.111.0.802.1.0
```

This prints `Hello`. N-DOT compiles to pure Python plus a small, stdlib-only support module (`ndot_runtime`).

---

## 1. Design rules

1. **Numbers are registry codes, not arbitrary values.** Every opcode has an entry in the registry, which defines its name, its operands, and how it lowers to Python.
2. **Opcodes are semantic paths.** The three digits of a core opcode are `domain · family · operation`. For example, `731` = math (7) → functions (3) → square root (1).
3. **`.` is the only separator.** It never means a decimal point.
4. **`0` is the only terminator.** A segment that is exactly `0` ends an instruction. No operand can ever be the bare segment `0`, so the stream always splits into instructions in exactly one way.
5. **Built-in redundancy.** Because every instruction is terminated *and* the registry gives its arity, a single corrupted or hallucinated digit is caught at check time instead of silently changing the meaning. This matters for code written by AI systems.

---

## 2. Lexical structure

### 2.1 Alphabet
- Allowed characters: `0`–`9` and `.` (ASCII 0x30–0x39, 0x2E).
- Any other byte, **including spaces, tabs, and newlines**, is error **N101**.
- File extension `.ndot`, ASCII encoding.

### 2.2 Segments
The source is split on `.` into **segments**. Each segment must:
- be non-empty. `..`, a leading `.`, or a trailing `.` is error **N102**;
- have no leading zeros, unless the segment is exactly `0`. `05` and `007` are error **N103**.

So every segment is either the **terminator** `0` or a **positive integer** (≥ 1).

### 2.3 Instructions
Segments are grouped into instructions at each terminator:

```text
OPCODE . OPERAND . OPERAND … . 0
```

- The first segment of a group is the **opcode**, and the rest are **operands**.
- The last segment of the program must be `0` (**N104**).
- An empty group (`0` straight after another `0`, or `0` at the very start) is error **N105**.

### 2.4 Lexer algorithm

```text
1. reject if any char ∉ {0-9, .}                → N101
2. segments = source.split(".")
3. reject empty segments                         → N102
4. reject segments with leading zeros (≠ "0")    → N103
5. reject if segments[-1] != "0"                 → N104
6. walk segments; on "0" close current group     → N105 if group is empty
7. each group → Instruction(opcode, operands, position)
```

Positions are reported as **instruction index** (1-based) plus **character offset**, e.g. `instruction 7 (char 58)`.

---

## 3. Execution model

### 3.1 Slots
- Values live in numbered **slots** `s1, s2, …` (slot numbers are ≥ 1, so `0` stays reserved).
- Slots are dynamically typed. A slot can hold an integer, decimal, text, flag, nothing, list, dictionary, tensor, model, or dataset.
- Each function call gets its **own slot frame**. The top level is frame 0.
- Implementations must support at least 4096 slots per frame.
- Reading a slot that has never been written is a check-time warning when the checker can prove it, and runtime error **N301** otherwise.

### 3.2 Operand kinds
The registry gives each operand one of these kinds:

| Kind | Meaning | Lowered as |
|---|---|---|
| `D` | Destination slot (written) | `sN = …` |
| `S` | Source slot (read) | `sN` |
| `L` | Literal positive integer | the integer itself |
| `C` | Enum code (opcode-specific table, starts at 1) | constant |
| `F` | Function id (literal ≥ 1) | `fN` |
| `…S` / `…L` | Variadic tail: zero or more of that kind, up to the terminator | |
| `[x]` | Optional trailing operand | |

### 3.3 Why literals need their own instructions
Operands are never `0`. Zero, negative numbers, decimals, and text are therefore created with **literal instructions** (`61x`) that write into a slot. Other instructions then refer to that slot. This keeps the terminator unambiguous without any escaping.

### 3.4 Program header
Every program must start with the version instruction `900.1.0` (**N205** if it is missing). An optional `901.0` halts the program explicitly.

---

## 4. Opcode space

### 4.1 Domains (first digit)

| Digit | Domain |
|---|---|
| 1 | Models |
| 2 | Tensors |
| 3 | Neural operations |
| 4 | Datasets |
| 5 | Control flow |
| 6 | Memory, literals, collections |
| 7 | Math, logic, conversion |
| 8 | Input / output |
| 9 | System |

### 4.2 Ranges

| Range | Use |
|---|---|
| `100–999` | **Core registry** (this spec). Frozen at v1.0. |
| `1000–9999` | Official extension packs (enabled with `903`) |
| `10000+` | Vendor / user registries (enabled with `903`) |

---

## 5. Core registry v0.1

Signature notation: `D:dest S:a …`. Python lowering uses `rt` for `ndot_runtime`.

### 5.1 System — `9xx`

| Op | Name | Signature | Python |
|---|---|---|---|
| 900 | version | `L:major [L:minor]` | *(header check only)* |
| 901 | halt | `[L:code]` | `raise SystemExit(code)` |
| 902 | assert | `S:cond [S:message]` | `assert sC, sM` |
| 903 | require registry | `L:registry_id` | load extension registry |
| 904 | seed | `L:seed` | `rt.seed(n)` |
| 909 | debug dump | — | `rt.dump(locals())` |

### 5.2 Memory, literals, collections — `6xx`

| Op | Name | Signature | Python |
|---|---|---|---|
| 601 | store (copy) | `D S` | `sD = sS` |
| 602 | load persistent | `D S:key` | `sD = rt.mem_load(sK)` |
| 603 | cache persistent | `S:key S:value` | `rt.mem_store(sK, sV)` |
| 604 | delete | `S` | `sS = None` |
| 610 | positive integer | `D L:value` | `sD = value` |
| 611 | negative integer | `D L:magnitude` | `sD = -magnitude` |
| 612 | zero | `D` | `sD = 0` |
| 613 | positive decimal | `D L:mantissa L:scale` | `sD = mantissa / 10**scale` (e.g. `613.4.314.2.0` → `3.14`) |
| 614 | negative decimal | `D L:mantissa L:scale` | `sD = -(mantissa / 10**scale)` |
| 615 | text | `D …L:codepoints` | `sD = "<decoded>"` (code point 0 is not representable; `615.D.0` = `""`) |
| 616 | true | `D` | `sD = True` |
| 617 | false | `D` | `sD = False` |
| 618 | nothing | `D` | `sD = None` |
| 620 | list | `D …S:items` | `sD = [sA, sB, …]` |
| 621 | append | `S:list S:value` | `sL.append(sV)` |
| 622 | get item | `D S:list S:index` | `sD = sL[sI]` (**0-based**) |
| 623 | set item | `S:list S:index S:value` | `sL[sI] = sV` |
| 624 | length | `D S` | `sD = len(sS)` |
| 625 | dictionary | `D` | `sD = {}` |
| 626 | set key | `S:dict S:key S:value` | `sM[sK] = sV` |
| 627 | get key | `D S:dict S:key` | `sD = sM[sK]` |
| 629 | range list | `D S:start S:end` | `sD = list(range(sA, sB + 1))` |

### 5.3 Math, logic, conversion — `7xx`
Arithmetic is polymorphic: it works on numbers, and element-wise on tensors (with broadcasting) through `rt`.

| Op | Name | Signature | Python |
|---|---|---|---|
| 701 | add | `D S S` | `sD = rt.add(sA, sB)` (plain `+` when both are known scalars/text) |
| 702 | subtract | `D S S` | `sD = rt.sub(sA, sB)` |
| 703 | multiply | `D S S` | `sD = rt.mul(sA, sB)` |
| 704 | divide | `D S S` | `sD = rt.div(sA, sB)` |
| 705 | dot product | `D S S` | `sD = rt.dot(sA, sB)` |
| 706 | modulo | `D S S` | `sD = sA % sB` |
| 707 | power | `D S S` | `sD = rt.pow(sA, sB)` |
| 708 | negate | `D S` | `sD = rt.neg(sA)` |
| 711 | equal | `D S S` | `sD = sA == sB` |
| 712 | not equal | `D S S` | `sD = sA != sB` |
| 713 | less than | `D S S` | `sD = sA < sB` |
| 714 | less or equal | `D S S` | `sD = sA <= sB` |
| 715 | greater than | `D S S` | `sD = sA > sB` |
| 716 | greater or equal | `D S S` | `sD = sA >= sB` |
| 721 | and | `D S S` | `sD = sA and sB` |
| 722 | or | `D S S` | `sD = sA or sB` |
| 723 | not | `D S` | `sD = not sA` |
| 731 | square root | `D S` | `sD = rt.sqrt(sA)` |
| 732 | exp | `D S` | `sD = rt.exp(sA)` |
| 733 | log | `D S` | `sD = rt.log(sA)` |
| 734 | abs | `D S` | `sD = rt.abs(sA)` |
| 735 | sum | `D S` | `sD = rt.sum(sA)` |
| 736 | max | `D S` | `sD = rt.max(sA)` |
| 737 | min | `D S` | `sD = rt.min(sA)` |
| 738 | mean | `D S` | `sD = rt.mean(sA)` |
| 741 | to integer | `D S` | `sD = int(sA)` |
| 742 | to decimal | `D S` | `sD = float(sA)` |
| 743 | to text | `D S` | `sD = str(sA)` |

### 5.4 Control flow — `5xx`
Blocks are opened by an instruction and closed by `509` (end). Blocks nest, and an unbalanced block is error **N204**.

| Op | Name | Signature | Python |
|---|---|---|---|
| 501 | if | `S:cond` | `if sC:` |
| 502 | while | `S:cond` | `while sC:` (the body must update `sC`) |
| 503 | repeat | `L:count` | `for _ in range(count):` |
| 504 | stop | — | `break` |
| 505 | next | — | `continue` |
| 506 | otherwise | — | `else:` (only directly inside `501`) |
| 507 | for range | `D:var S:start S:end` | `for sV in range(sA, sB + 1):` (inclusive) |
| 508 | for each | `D:var S:iterable` | `for sV in sI:` |
| 509 | end block | — | *(dedent)* |
| 510 | define function | `F:id [L:param_count]` | `def fN(s1, …, sP):` (params arrive in slots 1…P) |
| 511 | return | `[S:value]` | `return sV` / `return None` |
| 512 | call | `D F:id …S:args` | `sD = fN(sA, …)` |

Rules:
- `510` can appear only at the top level, so functions do not nest in v0.1. Function ids are global, and calls may come before the definition. The backend emits all `def`s first.
- `511` outside a function is error **N206**. `504`/`505` outside a loop is error **N207**.
- "Else-if" is written by nesting a `501` inside the `506` branch.

### 5.5 Input / output — `8xx`

| Op | Name | Signature | Python |
|---|---|---|---|
| 801 | input | `D [S:prompt]` | `sD = input(sP)` |
| 802 | output | `…S:values` | `print(sA, sB, …)` |
| 803 | read file | `D S:path` | `sD = rt.read_file(sP)` (needs `--allow-files`) |
| 804 | network fetch | `D S:url` | `sD = rt.fetch(sU)` via `urllib` (needs `--allow-network`) |
| 805 | write file | `S:path S:value` | `rt.write_file(sP, sV)` (needs `--allow-files`) |

### 5.6 Tensors — `2xx`
v0.1 tensors are a pure-Python `rt.Tensor` holding a flat `list[float]` and a `shape` tuple.

| Op | Name | Signature | Python |
|---|---|---|---|
| 201 | tensor | `D S:nested_list` | `sD = rt.tensor(sS)` |
| 202 | vector | `D …S:items` | `sD = rt.tensor([sA, sB, …])` |
| 203 | matrix | `D L:rows L:cols S:flat_list` | `sD = rt.tensor(sS).reshape(rows, cols)` |
| 204 | reshape | `D S …L:dims` | `sD = sS.reshape(*dims)` |
| 205 | normalize | `D S` | `sD = rt.l2_normalize(sS)` |
| 206 | zeros | `D …L:dims` | `sD = rt.zeros(*dims)` |
| 207 | ones | `D …L:dims` | `sD = rt.ones(*dims)` |
| 208 | random | `D L:seed …L:dims` | `sD = rt.randn(seed, *dims)` |
| 209 | shape | `D S` | `sD = list(sS.shape)` |
| 211 | matmul | `D S S` | `sD = rt.matmul(sA, sB)` |
| 212 | transpose | `D S` | `sD = rt.transpose(sS)` |
| 213 | to list | `D S` | `sD = sS.tolist()` |

### 5.7 Neural operations — `3xx`

| Op | Name | Signature | Python |
|---|---|---|---|
| 301 | linear | `D S:x S:weight S:bias` | `sD = rt.linear(sX, sW, sB)` |
| 302 | convolution 1-D | `D S:x S:kernel` | `sD = rt.conv1d(sX, sK)` |
| 303 | attention | `D S:q S:k S:v` | `sD = rt.attention(sQ, sK, sV)` (scaled dot-product) |
| 304 | activation | `D S C:kind` | `sD = rt.activate(sS, kind)` |
| 305 | embedding | `D S:table S:indices` | `sD = rt.embed(sT, sI)` |
| 306 | layer norm | `D S` | `sD = rt.layer_norm(sS)` |
| 307 | loss | `D S:pred S:target C:kind` | `sD = rt.loss(sP, sT, kind)` |

Activation codes (`304`): `1` relu · `2` sigmoid · `3` tanh · `4` softmax · `5` gelu · `6` identity.
Loss codes (`307`): `1` mean squared error · `2` cross-entropy · `3` binary cross-entropy.

### 5.8 Datasets — `4xx`

| Op | Name | Signature | Python |
|---|---|---|---|
| 401 | dataset | `D S:x S:y` | `sD = rt.Dataset(sX, sY)` |
| 402 | batch | `D S:dataset L:size` | `sD = sS.batches(size)` → list of datasets |
| 403 | sample | `D S:dataset S:index` | `sD = sS[sI]` → `[x_row, y_value]` |
| 404 | shuffle | `D S:dataset L:seed` | `sD = sS.shuffled(seed)` |
| 405 | split | `D:first D:second S:dataset L:percent` | `sA, sB = sS.split(percent / 100)` (percent 1–99) |
| 406 | load CSV | `D S:path` | `sD = rt.load_csv(sP)` (last column = target; needs `--allow-files`) |
| 407 | size | `D S` | `sD = len(sS)` |

### 5.9 Models — `1xx`

| Op | Name | Signature | Python |
|---|---|---|---|
| 101 | create model | `D C:arch …L:sizes` | `sD = rt.create_model(arch, *sizes)` |
| 102 | load model | `D S:path` | `sD = rt.load_model(sP)` (JSON weights) |
| 103 | inference | `D S:model S:x` | `sD = sM.predict(sX)` |
| 104 | train | `D:final_loss S:model S:dataset L:epochs S:learning_rate` | `sD = sM.fit(sS, epochs, sR)` (full-batch gradient descent, updates the model in place) |
| 105 | evaluate | `D S:model S:dataset` | `sD = sM.evaluate(sS)` (MSE for regression, accuracy for classification) |
| 106 | save model | `S:model S:path` | `sM.save(sP)` |
| 107 | parameters | `D S:model` | `sD = sM.parameters()` → list of tensors |

Architecture codes (`101`):

| Code | Architecture | Sizes |
|---|---|---|
| 1 | Linear regression | `in, out` |
| 2 | Logistic regression | `in` |
| 3 | Multi-layer perceptron (ReLU hidden layers) | `in, hidden…, out` |

Transformer architectures are reserved for the extension range together with the optional backends (roadmap v0.3).

---

## 6. Registry format

The normative registry ships as `ndot/registry.json`, generated from the tables above. Each entry looks like this:

```json
{
  "701": {
    "path": "7.0.1",
    "name": "add",
    "domain": "math",
    "operands": ["D:dest", "S:a", "S:b"],
    "python": "{dest} = rt.add({a}, {b})",
    "pure": true,
    "since": "0.1"
  },
  "507": {
    "path": "5.0.7",
    "name": "for_range",
    "domain": "control",
    "operands": ["D:var", "S:start", "S:end"],
    "python": "for {var} in range({start}, {end} + 1):",
    "opens_block": true,
    "since": "0.1"
  }
}
```

- `pure` marks instructions without side effects. The optimizer (v0.2) may fold or remove them.
- `permissions` (e.g. `["files"]`, `["network"]`) marks sandbox-gated opcodes.
- Extension registries use the same schema and are loaded by `903.<registry_id>.0`.

---

## 7. Validation (`ndot check`)

| Code | Stage | Meaning |
|---|---|---|
| N101 | Lexer | Illegal character (anything except digits and `.`) |
| N102 | Lexer | Empty segment (`..`, leading or trailing `.`) |
| N103 | Lexer | Leading zero in a segment |
| N104 | Lexer | Program does not end with the terminator `0` |
| N105 | Lexer | Empty instruction |
| N201 | Registry | Unknown opcode (or an extension opcode without `903`) |
| N202 | Registry | Wrong number of operands for the opcode |
| N203 | Registry | Enum code out of range (e.g. activation `9`) |
| N204 | Structure | Unbalanced block (`509` missing or extra) or misplaced `506` |
| N205 | Structure | Missing or unsupported `900` version header |
| N206 | Structure | `511` outside a function, or `510` nested |
| N207 | Structure | `504`/`505` outside a loop |
| N208 | Structure | Call to an undefined function id, or wrong argument count |
| N209 | Dataflow | Slot read before any write (warning when not provable) |
| N301 | Runtime | Slot read before write |
| N302 | Runtime | Type error (e.g. matmul shape mismatch), reported with the instruction index and its mnemonic |
| N303 | Runtime | Permission denied (file/network opcode without the flag) |

Example diagnostic:

```text
N202 at instruction 6 (char 41): opcode 701 (math.add) expects 3 operands [D S S], got 2: 701.3.1.0
```

---

## 8. Python backend

1. Emit the header `from ndot import ndot_runtime as rt` (only if `rt` is used).
2. Emit every function (`510` … `509`) as a top-level `def fN(s1, …):`.
3. Emit the top-level instructions in order, using each registry template and keeping an indentation stack for blocks.
4. Fold literal instructions straight into Python literals (`615` → `"Hello"`).
5. Attach `lineno = instruction index` to the generated AST, so runtime errors map back to N-DOT instructions.

Slots become plain local variables (`s1`, `s2`, …), so the generated code stays readable.

---

## 9. Disassembly and assembly (tooling only)

Programs written by people or AI models are always numeric. For debugging, `ndot dis` prints a mnemonic listing. **This listing is not N-DOT source.** `ndot asm` converts it back.

```text
#   op   mnemonic        operands
1   900  version         1
2   615  text            s1 "Hello"
3   802  output          s1
```

---

## 10. Examples

### 10.1 Hello

```text
900.1.0.615.1.72.101.108.108.111.0.802.1.0
```

| Instruction | Meaning |
|---|---|
| `900.1.0` | version 1 |
| `615.1.72.101.108.108.111.0` | s1 = "Hello" |
| `802.1.0` | print s1 |

```python
s1 = "Hello"
print(s1)
```

### 10.2 Arithmetic: 2 + 3

```text
900.1.0.610.1.2.0.610.2.3.0.701.3.1.2.0.802.3.0
```

```python
s1 = 2
s2 = 3
s3 = s1 + s2
print(s3)
```

### 10.3 Loop: print 1 to 10

```text
900.1.0.610.1.1.0.610.2.10.0.507.3.1.2.0.802.3.0.509.0
```

```python
s1 = 1
s2 = 10
for s3 in range(s1, s2 + 1):
    print(s3)
```

### 10.4 Function: square(7)

```text
900.1.0.510.1.1.0.703.2.1.1.0.511.2.0.509.0.610.1.7.0.512.2.1.1.0.802.2.0
```

| Instruction | Meaning |
|---|---|
| `510.1.1.0` | define f1 with 1 parameter (arrives in s1) |
| `703.2.1.1.0` | s2 = s1 × s1 |
| `511.2.0` | return s2 |
| `509.0` | end function |
| `610.1.7.0` | s1 = 7 (top-level frame) |
| `512.2.1.1.0` | s2 = f1(s1) |
| `802.2.0` | print s2 |

```python
def f1(s1):
    s2 = s1 * s1
    return s2

s1 = 7
s2 = f1(s1)
print(s2)
```

### 10.5 Condition with otherwise

```text
900.1.0.610.1.19.0.610.2.18.0.716.3.1.2.0.501.3.0.615.4.65.100.117.108.116.0.802.4.0.506.0.615.4.77.105.110.111.114.0.802.4.0.509.0
```

```python
s1 = 19
s2 = 18
s3 = s1 >= s2
if s3:
    s4 = "Adult"
    print(s4)
else:
    s4 = "Minor"
    print(s4)
```

### 10.6 AI: learn y = 2x, then predict x = 5

```text
900.1.0.904.42.0.610.1.1.0.610.2.2.0.610.3.3.0.610.4.4.0.610.5.2.0.610.6.4.0.610.7.6.0.610.8.8.0.620.9.1.0.620.10.2.0.620.11.3.0.620.12.4.0.620.13.9.10.11.12.0.201.14.13.0.202.15.5.6.7.8.0.401.16.14.15.0.101.17.1.1.1.0.613.18.1.2.0.104.19.17.16.500.18.0.610.20.5.0.620.21.20.0.620.22.21.0.201.23.22.0.103.24.17.23.0.802.24.0
```

| Instructions | Meaning |
|---|---|
| `900.1.0` · `904.42.0` | version 1, random seed 42 |
| `610.1.1.0` … `610.4.4.0` | s1–s4 = 1, 2, 3, 4 |
| `610.5.2.0` … `610.8.8.0` | s5–s8 = 2, 4, 6, 8 |
| `620.9.1.0` … `620.12.4.0` | s9–s12 = [1], [2], [3], [4] |
| `620.13.9.10.11.12.0` | s13 = [[1],[2],[3],[4]] |
| `201.14.13.0` | s14 = tensor(s13) — shape (4, 1) |
| `202.15.5.6.7.8.0` | s15 = vector [2, 4, 6, 8] |
| `401.16.14.15.0` | s16 = dataset(x = s14, y = s15) |
| `101.17.1.1.1.0` | s17 = linear regression, in = 1, out = 1 |
| `613.18.1.2.0` | s18 = 0.01 (mantissa 1, scale 2) |
| `104.19.17.16.500.18.0` | train s17 on s16 for 500 epochs at lr s18; s19 = final loss |
| `610.20.5.0` · `620.21.20.0` · `620.22.21.0` · `201.23.22.0` | s23 = tensor([[5]]) |
| `103.24.17.23.0` | s24 = predict(s17, s23) |
| `802.24.0` | print s24 → approximately `[[10.0]]` |

```python
from ndot import ndot_runtime as rt

rt.seed(42)
s1, s2, s3, s4 = 1, 2, 3, 4
s5, s6, s7, s8 = 2, 4, 6, 8
s9, s10, s11, s12 = [s1], [s2], [s3], [s4]
s13 = [s9, s10, s11, s12]
s14 = rt.tensor(s13)
s15 = rt.tensor([s5, s6, s7, s8])
s16 = rt.Dataset(s14, s15)
s17 = rt.create_model(1, 1, 1)
s18 = 0.01
s19 = s17.fit(s16, 500, s18)
s20 = 5
s21 = [s20]
s22 = [s21]
s23 = rt.tensor(s22)
s24 = s17.predict(s23)
print(s24)
```

*(The backend emits one assignment per instruction. The grouped tuple assignments above are shortened for readability.)*

---

## 11. Advanced Python Parity (Full Coverage)

To ensure N-DOT can map to **all** Python syntax, the following opcodes are included in the core:

### 11.1 Objects and Classes (OOP)
| Op | Name | Signature | Python |
|---|---|---|---|
| 520 | define class | `F:id [F:base_id]` | `class cN(base):` |
| 521 | instantiate | `D F:id …S:args` | `sD = cN(*args)` |
| 631 | get attribute | `D S:obj S:attr` | `sD = getattr(sO, sA)` |
| 632 | set attribute | `S:obj S:attr S:value`| `setattr(sO, sA, sV)` |

### 11.2 Exceptions
| Op | Name | Signature | Python |
|---|---|---|---|
| 530 | try | — | `try:` |
| 531 | catch | `[C:type] D:err_var` | `except type as sD:` |
| 532 | finally | — | `finally:` |
| 533 | raise | `S:err` | `raise sE` |

### 11.3 Async and Await
| Op | Name | Signature | Python |
|---|---|---|---|
| 540 | define async fn| `F:id [L:params]` | `async def fN(…):` |
| 541 | await | `D S:coroutine` | `sD = await sC` |

### 11.4 Generators
| Op | Name | Signature | Python |
|---|---|---|---|
| 550 | yield | `[S:value]` | `yield sV` |

---

## 12. Notes on the original brainstorm

- A stream like `132.232.343.432.3.34.3.3.4` is **invalid** under this spec: it has no terminator and `132` is not a registered opcode. This is intentional, because arbitrary numbers can't be maintained or checked.
- PLAN and N-DOT both lower to Python today. Roadmap v0.3 adds `plan build --target ndot`, which turns N-DOT into the shared intermediate representation for both languages.
