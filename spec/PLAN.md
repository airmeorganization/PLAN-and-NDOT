# PLAN Language Specification — v0.1 (draft)

PLAN is a **controlled-English** programming language that compiles to Python.
Its sentences read like English, but every sentence follows one of a fixed set of patterns. The compiler never guesses what a sentence means.

```text
Create a variable called age with value 19.
When age is greater than 17,
    show "Adult".
Otherwise,
    show "Minor".
```

```python
age = 19
if age > 17:
    print("Adult")
else:
    print("Minor")
```

---

## 1. Design rules

1. **The first word decides.** Each sentence begins with a *sentence verb* (`Create`, `Set`, `Show`, `When`, …). That word alone selects the grammar rule, so the parser needs only one token of lookahead at the start of a sentence.
2. **One meaning per phrase.** A phrase such as `is at least` always means `>=`. Synonyms are allowed, but they are listed explicitly in this spec.
3. **Punctuation carries the structure.** `.` ends a sentence and `,` ends a block header. Indentation (or an `End …` sentence) marks block bodies.
4. **Everything compiles to readable Python.** There is no hidden interpreter. The runtime helper module is very small (§9).

---

## 2. Lexical structure

### 2.1 Source
- UTF-8 text, extension `.plan`.
- Lines end with `\n` or `\r\n`.

### 2.2 Case
- **Keywords are case-insensitive.** `Show`, `show`, and `SHOW` are the same.
- **Identifiers are case-sensitive.** `age` and `Age` are different variables.

### 2.3 Tokens

| Token | Rule | Examples |
|---|---|---|
| Word | `[A-Za-z_][A-Za-z0-9_]*` | `age`, `total_score`, `show` |
| Integer | `[0-9]+` | `19`, `1000` |
| Decimal | `[0-9]+ "." [0-9]+` (a digit must follow the dot) | `3.14`, `0.5` |
| Text | `"` … `"` with escapes `\"` `\\` `\n` `\t` | `"Hello, world."` |
| Possessive | `'s` directly after a word | `math's pi` |
| Dotted module name | Word `.` Word, **only inside `Use` sentences** | `os.path` |
| Comma | `,` | |
| Sentence end | `.` followed by whitespace or end of file | |
| Parentheses | `(` `)` for grouping | |

**The period rule.** Outside text literals, a `.` ends a sentence only when it is followed by whitespace or end of file. `3.5` is therefore a decimal and `os.path` is a dotted name, while `show x.` ends a sentence.

### 2.4 Comments
A sentence that starts with `Note:` continues to the end of the line and is ignored.

```text
Note: this computes the average.
```

### 2.5 Noise words
The articles `a`, `an`, and `the` are accepted **only** where the grammar shows them in brackets, e.g. `Create [a|an] variable`. Anywhere else they are an error, which keeps the grammar deterministic.

### 2.6 Reserved words
These cannot be used as identifiers:

```text
create let set increase decrease add append remove show ask use return call
stop skip when if otherwise for every while repeat try on end note python
is not and or plus minus times divided by modulo power of to from in
true false yes no nothing it with called value
```

*Contextual* words (`number`, `text`, `list`, `flag`, `module`, `function`, `variable`, `times`, `steps`) act as keywords only in the positions where the grammar uses them. Everywhere else they are ordinary identifiers, so `For every number from 1 to 10, show number.` is valid.

---

## 3. Sentence and block structure

### 3.1 Simple sentences
A simple statement ends with `.`, and it may run across several lines:

```text
Create a variable called message with value
    "This sentence continues on the next line".
```

### 3.2 Blocks
A **block header** ends with `,` (or `.` before a terminated body). The body can take one of three forms, and all three compile to the same thing:

| Form | Rule | Example |
|---|---|---|
| **Inline** | The body is one sentence on the same line as the header | `When x is greater than 3, show "Big".` |
| **Indented** | The body is the following lines, indented further than the header (Python-style). An `End …` sentence is optional | see below |
| **Terminated** | The body is not indented and continues until the matching `End <kind>.` | see below |

```text
Note: indented form
When x is greater than 3,
    show "Big".
    show "Really big".
Otherwise,
    show "Small".

Note: terminated form
Create a function called add that accepts number a and number b.
Return a plus b.
End function.
```

Indentation must be consistent within a file: either tabs or a fixed number of spaces (the first indented line sets the unit). Mixing them is error **P204**.

`End` sentences: `End when.`, `End for.`, `End while.`, `End repeat.`, `End loop.` (closes any loop), `End function.`, `End try.`

---

## 4. Grammar (EBNF)

Notation: `"word"` matches a keyword case-insensitively, `[x]` is optional, `{x}` means zero or more, and `NAME` is an identifier.

```ebnf
program        = { sentence } EOF ;
sentence       = statement "." | block | note ;

(* ---------- simple statements ---------- *)
statement      = declare | set | increase | decrease | add | append | remove
               | show | ask | use | shared | return | call_stmt
               | stop | skip | python_raw ;

declare        = "create" ["a"|"an"] "variable" "called" NAME "with" "value" expr
               | "let" NAME "be" expr ;
set            = "set" target "to" expr ;
increase       = "increase" target "by" expr ;
decrease       = "decrease" target "by" expr ;
add            = "add" expr "to" target ;              (* target += expr        *)
append         = "append" expr "to" target ;           (* target.append(expr)   *)
remove         = "remove" expr "from" target ;         (* target.remove(expr)   *)
show           = "show" expr { "followed" "by" expr } ;
ask            = "ask" ["for" ("a" "number" | "a" "whole" "number") "with"] expr
                 "and" "store" "the" "answer" "in" NAME ;
use            = "use" ["the"] MODULE "module" ["as" NAME]
               | "use" NAME { ("," | "and") NAME } "from" ["the"] MODULE "module" ;
shared         = "use" "the" "shared" "variable" NAME ;
return         = "return" ( expr | "nothing" ) ;
call_stmt      = call ;
stop           = "stop" "the" ( "loop" | "program" ) ;
skip           = "skip" ( "to" "the" "next" "round" | "this" "round" ) ;
python_raw     = "python:" RAW_LINE ;                  (* escape hatch, sandbox-gated *)

target         = NAME
               | "item" expr "of" NAME
               | "the" ("first"|"last") "item" "of" NAME
               | "the" expr "entry" "of" NAME
               | NAME "'s" NAME ;

(* ---------- blocks ---------- *)
block          = when_chain | for_range | for_each | while_loop | repeat_loop
               | function_def | try_block ;

when_chain     = ("when"|"if") condition "," body
                 { "otherwise" ("when"|"if") condition "," body }
                 [ "otherwise" "," body ] ;
for_range      = "for" "every" NAME "from" expr "to" expr
                 ["in" "steps" "of" expr] "," body ;
for_each       = "for" "every" NAME "in" expr "," body ;
while_loop     = ("while"|"as" "long" "as") condition "," body ;
repeat_loop    = "repeat" expr "times" "," body ;
function_def   = "create" ["a"|"an"] "function" "called" NAME
                 ["that" "accepts" param { ("," | "and") param }]
                 ["and" "gives" "back" TYPE] ("," | ".") body ;
param          = [TYPE] NAME ;
TYPE           = "number" | "whole" "number" | "text" | "list" | "dictionary" | "flag" ;
try_block      = "try" "," body
                 "on" "failure" ["as" NAME] "," body ;

body           = inline_body | indented_body | terminated_body ;

(* ---------- expressions (lowest → highest precedence) ---------- *)
expr           = or_expr ;
condition      = expr ;
or_expr        = and_expr { "or" and_expr } ;
and_expr       = not_expr { "and" not_expr } ;
not_expr       = "not" not_expr | comparison ;
comparison     = additive [ comp_op additive
                          | "is" ["not"] "between" additive "and" additive
                          | "is" ["not"] "empty"
                          | "is" ["not"] "nothing"
                          | "contains" additive ] ;
additive       = multiplicative { ("plus" | "minus") multiplicative } ;
multiplicative = power { ("times" | "divided" "by" | "modulo") power } ;
power          = unary [ "to" "the" "power" "of" power ] ;   (* right-assoc *)
unary          = "negative" unary | postfix ;
postfix        = primary { postfix_op } ;
primary        = NUMBER | TEXT | "true" | "yes" | "false" | "no" | "nothing"
               | NAME | NAME "'s" NAME
               | list_lit | dict_lit | phrase | call | index
               | "(" expr ")" ;

list_lit       = "an" "empty" "list"
               | "a" "list" "of" item { "," item } [ ["," ] "and" item ] ;
item           = additive ;           (* logical 'and'/'or' inside items need ( ) *)
dict_lit       = "an" "empty" "dictionary" ;
index          = "item" expr "of" postfix
               | "the" ("first"|"last") "item" "of" postfix
               | "the" expr "entry" "of" postfix ;
call           = "call" callee ["with" arg { ("," | "and") arg }]
               | "the" "result" "of" callee ["with" arg { ("," | "and") arg }] ;
callee         = NAME | NAME "'s" NAME ;
arg            = additive | NAME "set" "to" additive ;   (* keyword argument *)
```

### 4.1 Disambiguation rules
- **`and` inside argument and list positions** separates items. Logical `and`/`or` inside an item must be wrapped in parentheses: `call check with (a and b) and c`.
- **Commas inside a block header** belong to the innermost open list literal or call. The first top-level comma after the condition ends the header.
- **`is` followed by an expression** means equality: `When answer is "yes", …`.
- **`times`** is multiplication in expressions, but ends the count in a `Repeat … times` header.
- **Phrases bind tightly:** `square root of x plus 1` means `math.sqrt(x) + 1`. Write `square root of (x plus 1)` for the other reading.

---

## 5. Operators

### 5.1 Arithmetic

| PLAN | Python |
|---|---|
| `a plus b` | `a + b` |
| `a minus b` | `a - b` |
| `a times b` | `a * b` |
| `a divided by b` | `a / b` |
| `a modulo b` | `a % b` |
| `a to the power of b` | `a ** b` |
| `negative a` | `-a` |

### 5.2 Comparison

| PLAN (synonyms separated by /) | Python |
|---|---|
| `is greater than` / `is more than` | `>` |
| `is less than` / `is fewer than` | `<` |
| `is greater than or equal to` / `is at least` | `>=` |
| `is less than or equal to` / `is at most` | `<=` |
| `is equal to` / `equals` / `is` | `==` |
| `is not equal to` / `is not` | `!=` |
| `is between A and B` | `A <= x <= B` |
| `is in` / `is not in` | `in` / `not in` |
| `contains` | `b in a` |
| `is empty` / `is not empty` | `len(x) == 0` / `len(x) > 0` |
| `is nothing` / `is not nothing` | `is None` / `is not None` |

### 5.3 Logic
`and`, `or`, `not` → `and`, `or`, `not`.

---

## 6. Statements → Python

| PLAN | Python |
|---|---|
| `Create a variable called x with value 5.` | `x = 5` |
| `Let x be 5.` | `x = 5` |
| `Set x to x plus 1.` | `x = x + 1` |
| `Increase score by 10.` | `score += 10` |
| `Decrease lives by 1.` | `lives -= 1` |
| `Add 5 to total.` | `total += 5` |
| `Append "milk" to groceries.` | `groceries.append("milk")` |
| `Remove "milk" from groceries.` | `groceries.remove("milk")` |
| `Set item 2 of scores to 99.` | `scores[2 - 1] = 99` → `scores[1] = 99` (constant-folded) |
| `Set the "city" entry of person to "Chennai".` | `person["city"] = "Chennai"` |
| `Show x.` | `print(x)` |
| `Show "Hi, " followed by name followed by "!".` | `print("Hi, ", name, "!", sep="")` |
| `Ask "Name? " and store the answer in name.` | `name = input("Name? ")` |
| `Ask for a number with "Age? " and store the answer in age.` | `age = plan_rt.to_number(input("Age? "))` |
| `Use the math module.` | `import math` |
| `Use the requests module as network.` | `import requests as network` |
| `Use sqrt and pi from the math module.` | `from math import sqrt, pi` |
| `Use the shared variable count.` | `global count` |
| `Return a plus b.` | `return a + b` |
| `Call greet with "Surya".` | `greet("Surya")` |
| `Call network's get with url and timeout set to 5.` | `network.get(url, timeout=5)` |
| `Stop the loop.` | `break` |
| `Skip to the next round.` | `continue` |
| `Stop the program.` | `raise SystemExit` |

### 6.1 Blocks → Python

| PLAN header | Python |
|---|---|
| `When c,` / `If c,` | `if c:` |
| `Otherwise when c,` | `elif c:` |
| `Otherwise,` | `else:` |
| `For every n from 1 to 10,` | `for n in range(1, 10 + 1):` |
| `For every n from 10 to 1 in steps of -1,` | `for n in range(10, 1 - 1, -1):` (bounds are inclusive, adjusted by the step's sign) |
| `For every name in names,` | `for name in names:` |
| `While c,` / `As long as c,` | `while c:` |
| `Repeat 3 times,` | `for _plan_i in range(3):` |
| `Create a function called f that accepts number a and text b,` | `def f(a: float, b: str):` |
| `… and gives back number,` | `def f(...) -> float:` |
| `Try,` … `On failure as problem,` | `try:` … `except Exception as problem:` |

Type words become Python annotations. They are documentation only and are not enforced in v0.1: `number` → `float`, `whole number` → `int`, `text` → `str`, `list` → `list`, `dictionary` → `dict`, `flag` → `bool`.

---

## 7. Collections and indexing

- **Lists:** `an empty list`, `a list of 7`, `a list of 1 and 2`, `a list of "a", "b", and "c"`.
- **Dictionaries:** `an empty dictionary`, then `Set the "k" entry of d to v.`
- **Indexing is 1-based in PLAN.** `item 1 of names` is the first element. The compiler emits `names[n - 1]` and folds constants where possible.
- `the first item of x` → `x[0]`, `the last item of x` → `x[-1]`.
- An out-of-range index raises a PLAN-worded error: *"Line 7: there is no item 5 in names — it only has 3 items."*

---

## 8. Phrase library

Phrases are built-in expression patterns that expand into Python and add any needed `import` automatically. The library lives in `phrases.py` as a table, so new phrases need no grammar changes.

| PLAN phrase | Python | Auto-import |
|---|---|---|
| `square root of x` | `math.sqrt(x)` | `math` |
| `absolute value of x` | `abs(x)` | |
| `length of x` / `the number of items in x` | `len(x)` | |
| `the sum of x` | `sum(x)` | |
| `the largest of x` / `the smallest of x` | `max(x)` / `min(x)` | |
| `the average of x` | `statistics.mean(x)` | `statistics` |
| `x rounded` / `x rounded to n places` | `round(x)` / `round(x, n)` | |
| `x as text` | `str(x)` | |
| `x as a number` / `x as a whole number` | `plan_rt.to_number(x)` / `int(x)` | |
| `x in uppercase` / `x in lowercase` | `x.upper()` / `x.lower()` | |
| `x sorted` / `x reversed` | `sorted(x)` / `list(reversed(x))` | |
| `x split by s` | `x.split(s)` | |
| `x joined with s` | `s.join(str(i) for i in x)` | |
| `a random number from a to b` | `random.randint(a, b)` | `random` |
| `a random item from x` | `random.choice(x)` | `random` |
| `the current time` | `datetime.datetime.now()` | `datetime` |

Postfix phrases (`as text`, `rounded`, `sorted`, …) bind tighter than arithmetic: `a plus b as text` means `a + str(b)`.

---

## 9. Semantics

### 9.1 Scope
- Top-level variables are module globals.
- Function bodies have their own local scope, and parameters are locals.
- Assigning to a top-level variable inside a function requires `Use the shared variable x.` (→ `global x`).
- Loop variables stay visible after the loop, matching Python.

### 9.2 Declaration rules
- `Create`/`Let` introduces a new name. Re-creating a name that already exists in the same scope is error **P302**.
- `Set`, `Increase`, `Decrease`, `Add`, `Append`, and `Remove` require a name that already exists (**P303**).
- `Ask … store the answer in x` and `For every x …` declare `x` if it does not exist yet.

### 9.3 Functions
- Functions are hoisted: calling a function earlier in the file than its definition is allowed. Codegen emits every `def` before the top-level statements.
- Calling a PLAN function with the wrong number of arguments is a compile-time error (**P308**). Calls to Python callables are checked at runtime only.

### 9.4 Runtime helper module (`plan_rt`)
This is the only non-stdlib code that generated programs import. It is kept small:
- `to_number(s)` → `int` if the value is integral, otherwise `float`. Raises a PLAN-worded error otherwise.
- `item(seq, n, line)` → 1-based indexing with English error messages (used when `n` is not a constant).
- An exception hook that maps Python tracebacks back to PLAN line numbers through the source map.

---

## 10. Compilation pipeline

```text
PLAN source
  → Sentence lexer      (tokens + INDENT/DEDENT + sentence boundaries)
  → Parser              (recursive descent, first-word dispatch)
  → PLAN AST            (dataclasses in ast_nodes.py)
  → Semantic analyzer   (scopes, declarations, imports, arity, diagnostics)
  → Python AST          (stdlib `ast` nodes with lineno = PLAN line)
  → compile() / ast.unparse()
  → CPython
```

Generated Python AST nodes carry the **PLAN line number** as their `lineno`, so tracebacks point at PLAN lines with no extra work. `ast.unparse` produces the readable `.py` output for `plan build`.

---

## 11. Diagnostics

Every message is plain English and names the line. Where a fix is likely, it includes a "did you mean" suggestion (via `difflib`).

| Code | Stage | Example message |
|---|---|---|
| P101 | Lexer | Line 3: this text is never closed — add a `"` at the end. |
| P102 | Lexer | Line 8: I don't recognise the character `@`. |
| P103 | Lexer | Line 12: the last sentence needs a period at the end. |
| P201 | Parser | Line 5: I don't understand sentences that start with "Make". Did you mean "Create"? |
| P202 | Parser | Line 6: after "is greater than" I expected a value. |
| P203 | Parser | Line 9: this function is never finished — indent its body or add "End function.". |
| P204 | Parser | Line 14: indentation mixes tabs and spaces. |
| P205 | Parser | Line 20: "Otherwise" must follow a "When" block. |
| P301 | Semantic | Line 4: I don't know a variable called `agee`. Did you mean `age`? |
| P302 | Semantic | Line 7: `age` already exists. Use "Set age to …" to change it. |
| P303 | Semantic | Line 9: you can't set `total` before creating it. |
| P304 | Semantic | Line 11: "Return" can only be used inside a function. |
| P305 | Semantic | Line 15: "Stop the loop" can only be used inside a loop. |
| P306 | Semantic | Line 1: I can't find a Python module called `reqeusts`. Did you mean `requests`? |
| P308 | Semantic | Line 18: `add` needs 2 values but was given 3. |

---

## 12. Sandbox

- `Python:` raw lines are **disabled by default**. Enable them with `plan run --allow-python`.
- Imports are checked against an allow-list (default: the whole stdlib except `os`, `subprocess`, `socket`, `ctypes`, and `shutil`). `--allow-all-modules` lifts the restriction.

---

## 13. Complete examples

### 13.1 Grades

```text
Create a function called grade_for that accepts number score and gives back text,
    When score is at least 90,
        return "A".
    Otherwise when score is at least 75,
        return "B".
    Otherwise,
        return "C".

Create a variable called scores with value a list of 95, 82, and 61.
For every score in scores,
    show score followed by " → " followed by call grade_for with score.
```

```python
def grade_for(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    else:
        return "C"

scores = [95, 82, 61]
for score in scores:
    print(score, " → ", grade_for(score), sep="")
```

### 13.2 Modules and phrases

```text
Use the math module.
Create a variable called x with value 25.
Create a variable called result with value square root of x.
Show result.
Show math's pi rounded to 3 places.
```

```python
import math

x = 25
result = math.sqrt(x)
print(result)
print(round(math.pi, 3))
```

### 13.3 Interactive loop with error handling

```text
Create a variable called total with value 0.
Repeat 3 times,
    Try,
        Ask for a number with "Enter a number: " and store the answer in n.
        Add n to total.
    On failure,
        show "That was not a number, skipping.".
Show "Total: " followed by total.
```

```python
import plan_rt

total = 0
for _plan_i in range(3):
    try:
        n = plan_rt.to_number(input("Enter a number: "))
        total += n
    except Exception:
        print("That was not a number, skipping.")
print("Total: ", total, sep="")
```

## 14. Advanced Python Features (Roadmap v0.2+ Parity)

> **Design Boundary Note:** The **Core v0.1** specification covers statements, blocks, conditions, loops, functions, collections, indexing, phrase libraries, and exceptions as detailed in Sections 1–13.
>
> The patterns documented below define the native grammar designs for advanced Python parity (OOP classes, async/await, generators, comprehensions, decorators, context managers) slated for native compiler implementation in **v0.2+**. For v0.1 workflows requiring these features, developers can use the `python:` block (§15).

### 14.1 Classes and Objects
```text
Describe a kind of thing called Dog inheriting from Animal,
    Create a function called __init__ that accepts text name,
        Set the shared variable name to name.
    Create a function called bark,
        Show "Woof!".
End kind.

Create a variable called my_dog with value a new Dog with "Rex".
Call my_dog's bark.
```
**Python:** `class Dog(Animal): ...` and `my_dog = Dog("Rex"); my_dog.bark()`

### 14.2 Async and Await
```text
Create an async function called fetch_data that accepts text url,
    Wait for call network's get with url.
End function.
```
**Python:** `async def fetch_data(url): await network.get(url)`

### 14.3 Generators (Yield)
```text
Create a function called count_up,
    For every i from 1 to 10,
        Yield i.
End function.
```
**Python:** `def count_up(): for i in range(1, 11): yield i`

### 14.4 Exceptions (Try/Catch)
```text
Try,
    Show 1 divided by 0.
On failure with ZeroDivisionError as e,
    Show "Cannot divide by zero".
Always,
    Show "Done".
Raise ValueError with "Invalid".
```

### 14.5 List Comprehensions
```text
Create a variable called squares with value a list of (x times x) for every x in numbers when x is greater than 2.
```
**Python:** `squares = [x * x for x in numbers if x > 2]`

### 14.6 Decorators
```text
Decorate with timer,
Create a function called slow_task,
    ...
```
**Python:** `@timer\ndef slow_task(): ...`

### 14.7 Context Managers (With)
```text
With call open with "file.txt" as f,
    Show call f's read.
```
**Python:** `with open("file.txt") as f: print(f.read())`

### 14.8 Lambdas
```text
Create a variable called f with value an inline function taking x that gives x times 2.
```
**Python:** `f = lambda x: x * 2`

---

## 15. The Escape Hatch
For any feature not natively mapped, use the `python:` block.
```text
python:
    import itertools
    def complex_stuff(): pass
```
