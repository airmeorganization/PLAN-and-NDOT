from dataclasses import dataclass, field
from typing import List, Optional, Union, Any, Dict, Tuple

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
    op: str # '+', '-', '*', '/', '%', '**', '==', '!=', '<', '<=', '>', '>=', 'and', 'or', 'in', 'not in'
    right: Expr

@dataclass
class UnaryOp(Expr):
    op: str # '-', 'not'
    operand: Expr

@dataclass
class Between(Expr):
    expr: Expr
    low: Expr
    high: Expr
    negated: bool = False

@dataclass
class IsEmpty(Expr):
    expr: Expr
    negated: bool = False

@dataclass
class IsNothing(Expr):
    expr: Expr
    negated: bool = False

@dataclass
class Call(Expr):
    callee: Expr
    args: List[Expr] = field(default_factory=list)
    kwargs: Dict[str, Expr] = field(default_factory=dict)

@dataclass
class MemberAccess(Expr):
    target: Expr
    member: str

@dataclass
class Index(Expr):
    target: Expr
    index: Expr

@dataclass
class FirstItem(Expr):
    target: Expr

@dataclass
class LastItem(Expr):
    target: Expr

@dataclass
class EntryIndex(Expr):
    target: Expr
    key: Expr

@dataclass
class ListLiteral(Expr):
    items: List[Expr] = field(default_factory=list)

@dataclass
class DictLiteral(Expr):
    pass

@dataclass
class Phrase(Expr):
    name: str
    args: List[Expr] = field(default_factory=list)

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
    followed_by: bool = False

@dataclass
class Ask(Statement):
    prompt: Expr
    target: str
    kind: str = 'text' # 'text', 'number', 'whole_number'

@dataclass
class UseModule(Statement):
    module: str
    alias: Optional[str] = None

@dataclass
class UseFromModule(Statement):
    names: List[str] = field(default_factory=list)
    module: str = ""

@dataclass
class UseShared(Statement):
    name: str

@dataclass
class Return(Statement):
    value: Optional[Expr] = None

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
class WhenCase:
    condition: Expr
    body: List[Statement]

@dataclass
class WhenBlock(Statement):
    cases: List[WhenCase]
    otherwise_body: Optional[List[Statement]] = None

@dataclass
class ForRange(Statement):
    var_name: str
    start: Expr
    end: Expr
    step: Optional[Expr]
    body: List[Statement]

@dataclass
class ForEach(Statement):
    var_name: str
    iterable: Expr
    body: List[Statement]

@dataclass
class WhileLoop(Statement):
    condition: Expr
    body: List[Statement]

@dataclass
class RepeatLoop(Statement):
    count: Expr
    body: List[Statement]

@dataclass
class FunctionDef(Statement):
    name: str
    params: List[Tuple[Optional[str], str]] # (type, name)
    return_type: Optional[str]
    body: List[Statement]

@dataclass
class TryBlock(Statement):
    try_body: List[Statement]
    failure_name: Optional[str]
    failure_body: List[Statement]

@dataclass
class Program(ASTNode):
    statements: List[Statement]
