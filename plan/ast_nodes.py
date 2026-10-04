from dataclasses import dataclass
from typing import List, Optional, Union, Any

@dataclass
class ASTNode:
    line: int
    column: int

# --- Expressions ---

@dataclass
class Expr(ASTNode):
    pass

@dataclass
class Literal(Expr):
    value: Any # int, float, str, bool, None

@dataclass
class Identifier(Expr):
    name: str

@dataclass
class BinaryOp(Expr):
    left: Expr
    op: str
    right: Expr

@dataclass
class UnaryOp(Expr):
    op: str
    operand: Expr

@dataclass
class Call(Expr):
    callee: Expr
    args: List[Expr]

@dataclass
class MemberAccess(Expr):
    target: Expr
    member: str

@dataclass
class Index(Expr):
    target: Expr
    index: Expr

@dataclass
class ListLiteral(Expr):
    items: List[Expr]

@dataclass
class DictLiteral(Expr):
    pass # Empty dict for v0.1

@dataclass
class Phrase(Expr):
    name: str
    args: List[Expr]

# --- Statements ---

@dataclass
class Statement(ASTNode):
    pass

@dataclass
class Declare(Statement):
    name: str
    value: Expr

@dataclass
class SetStmt(Statement):
    target: Expr
    value: Expr

@dataclass
class ModifyStmt(Statement):
    target: Expr
    op: str # '+', '-', 'append', 'remove'
    value: Expr

@dataclass
class Show(Statement):
    exprs: List[Expr]

@dataclass
class Ask(Statement):
    prompt: Expr
    target: str
    is_number: bool

@dataclass
class UseModule(Statement):
    module: str
    alias: Optional[str]

@dataclass
class UseFromModule(Statement):
    names: List[str]
    module: str

@dataclass
class UseShared(Statement):
    name: str

@dataclass
class Return(Statement):
    value: Optional[Expr]

@dataclass
class CallStmt(Statement):
    call: Call

@dataclass
class Stop(Statement):
    target: str # 'loop' or 'program'

@dataclass
class Skip(Statement):
    pass

@dataclass
class PythonRaw(Statement):
    code: str

# --- Blocks ---

@dataclass
class Block(Statement):
    body: List[Statement]

@dataclass
class IfBlock(Block):
    condition: Expr
    else_if_blocks: List['IfBlock']
    else_body: Optional[List[Statement]]

@dataclass
class ForRange(Block):
    var_name: str
    start: Expr
    end: Expr
    step: Optional[Expr]

@dataclass
class ForEach(Block):
    var_name: str
    iterable: Expr

@dataclass
class WhileLoop(Block):
    condition: Expr

@dataclass
class RepeatLoop(Block):
    count: Expr

@dataclass
class FunctionDef(Block):
    name: str
    params: List[tuple[Optional[str], str]] # type, name
    return_type: Optional[str]

@dataclass
class TryBlock(Block):
    failure_name: Optional[str]
    failure_body: List[Statement]

@dataclass
class Program(ASTNode):
    statements: List[Statement]
