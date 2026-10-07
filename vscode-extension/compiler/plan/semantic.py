"""PLAN Semantic Analyzer (spec/PLAN.md §9, §11).

Performs scope resolution, declaration checks (use-before-create, duplicate definitions),
function hoisting, loop/function context validation, and call arity checks.
Reports English diagnostics with 'did you mean' suggestions.
"""
import difflib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from plan.ast_nodes import *
from common.diagnostics import CompileError

@dataclass
class FunctionInfo:
    name: str
    param_count: int
    line: int

class Scope:
    def __init__(self, name: str, is_function: bool = False, is_loop: bool = False, parent: Optional['Scope'] = None):
        self.name = name
        self.is_function = is_function
        self.is_loop = is_loop
        self.parent = parent
        self.symbols: Set[str] = set()
        self.shared_symbols: Set[str] = set()

    def declare(self, name: str):
        self.symbols.add(name)

    def is_declared(self, name: str) -> bool:
        if name in self.symbols or name in self.shared_symbols:
            return True
        if self.parent:
            return self.parent.is_declared(name)
        return False

    def is_in_function(self) -> bool:
        if self.is_function:
            return True
        return self.parent.is_in_function() if self.parent else False

    def is_in_loop(self) -> bool:
        if self.is_loop:
            return True
        return self.parent.is_in_loop() if self.parent else False

    def all_visible_names(self) -> Set[str]:
        names = set(self.symbols)
        if self.parent:
            names.update(self.parent.all_visible_names())
        return names

class SemanticAnalyzer:
    """Walks the PLAN AST and verifies scopes, declarations, and semantics."""

    def __init__(self):
        self.functions: Dict[str, FunctionInfo] = {}
        self.module_scope = Scope(name='module', is_function=False, is_loop=False)
        self.current_scope = self.module_scope
        # Known standard libraries/globals that are allowed
        self.builtin_names = {'print', 'len', 'range', 'input', 'math', 'statistics', 'random', 'datetime', 'plan_rt'}

    def analyze(self, program: Program):
        # Pass 1: Hoist and register all top-level functions
        for stmt in program.statements:
            if isinstance(stmt, FunctionDef):
                if stmt.name in self.functions:
                    raise CompileError(
                        f"Line {stmt.line}: '{stmt.name}' already exists. A function cannot be declared twice.",
                        line=stmt.line, column=stmt.column, code="P302"
                    )
                self.functions[stmt.name] = FunctionInfo(stmt.name, len(stmt.params), stmt.line)
                self.module_scope.declare(stmt.name)

        # Pass 2: Analyze statements
        for stmt in program.statements:
            self.visit_stmt(stmt)

    def enter_scope(self, name: str, is_function: bool = False, is_loop: bool = False) -> Scope:
        new_scope = Scope(name, is_function=is_function, is_loop=is_loop, parent=self.current_scope)
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self):
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    # --- Statement Visitors ---

    def visit_stmt(self, node: Statement):
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method:
            method(node)

    def visit_Declare(self, node: Declare):
        self.visit_expr(node.value)
        # Check duplicate declaration in the current local scope
        if node.name in self.current_scope.symbols:
            raise CompileError(
                f"Line {node.line}: '{node.name}' already exists. Use 'Set {node.name} to …' to change it.",
                line=node.line, column=node.column, code="P302"
            )
        self.current_scope.declare(node.name)

    def visit_SetStmt(self, node: SetStmt):
        self.visit_expr(node.value)
        self.check_target_exists(node.target, node.line, node.column)

    def visit_ModifyStmt(self, node: ModifyStmt):
        self.visit_expr(node.value)
        self.check_target_exists(node.target, node.line, node.column)

    def check_target_exists(self, target: Expr, line: int, column: int):
        if isinstance(target, Identifier):
            name = target.name
            if not self.current_scope.is_declared(name):
                suggestion = self.get_suggestion(name)
                sugg_msg = f" Did you mean '{suggestion}'?" if suggestion else ""
                raise CompileError(
                    f"Line {line}: you can't set '{name}' before creating it.{sugg_msg}",
                    line=line, column=column, code="P303"
                )
        elif isinstance(target, (Index, FirstItem, LastItem, EntryIndex, MemberAccess)):
            # Check the base object exists
            base = getattr(target, 'target', None)
            if base:
                self.check_target_exists(base, line, column)
            if hasattr(target, 'index'):
                self.visit_expr(target.index)
            if hasattr(target, 'key'):
                self.visit_expr(target.key)

    def visit_Show(self, node: Show):
        for expr in node.exprs:
            self.visit_expr(expr)

    def visit_Ask(self, node: Ask):
        self.visit_expr(node.prompt)
        # Ask declares the target if not already declared
        self.current_scope.declare(node.target)

    def visit_UseModule(self, node: UseModule):
        name = node.alias if node.alias else node.module
        self.current_scope.declare(name)

    def visit_UseFromModule(self, node: UseFromModule):
        for name in node.names:
            self.current_scope.declare(name)

    def visit_UseShared(self, node: UseShared):
        self.current_scope.shared_symbols.add(node.name)

    def visit_Return(self, node: Return):
        if not self.current_scope.is_in_function():
            raise CompileError(
                f"Line {node.line}: 'Return' can only be used inside a function.",
                line=node.line, column=node.column, code="P304"
            )
        if node.value:
            self.visit_expr(node.value)

    def visit_CallStmt(self, node: CallStmt):
        self.visit_expr(node.call)

    def visit_Stop(self, node: Stop):
        if node.target == 'loop':
            if not self.current_scope.is_in_loop():
                raise CompileError(
                    f"Line {node.line}: 'Stop the loop' can only be used inside a loop.",
                    line=node.line, column=node.column, code="P305"
                )

    def visit_Skip(self, node: Skip):
        if not self.current_scope.is_in_loop():
            raise CompileError(
                f"Line {node.line}: 'Skip' can only be used inside a loop.",
                line=node.line, column=node.column, code="P305"
            )

    def visit_PythonRaw(self, node: PythonRaw):
        pass

    # --- Block Visitors ---

    def visit_WhenBlock(self, node: WhenBlock):
        for case in node.cases:
            self.visit_expr(case.condition)
            self.enter_scope("when", is_loop=self.current_scope.is_loop)
            for stmt in case.body:
                self.visit_stmt(stmt)
            self.exit_scope()

        if node.otherwise_body:
            self.enter_scope("otherwise", is_loop=self.current_scope.is_loop)
            for stmt in node.otherwise_body:
                self.visit_stmt(stmt)
            self.exit_scope()

    def visit_ForRange(self, node: ForRange):
        self.visit_expr(node.start)
        self.visit_expr(node.end)
        if node.step:
            self.visit_expr(node.step)

        # Loop variable stays visible in enclosing scope (§9.1)
        self.current_scope.declare(node.var_name)

        self.enter_scope("for_range", is_loop=True)
        for stmt in node.body:
            self.visit_stmt(stmt)
        self.exit_scope()

    def visit_ForEach(self, node: ForEach):
        self.visit_expr(node.iterable)
        self.current_scope.declare(node.var_name)

        self.enter_scope("for_each", is_loop=True)
        for stmt in node.body:
            self.visit_stmt(stmt)
        self.exit_scope()

    def visit_WhileLoop(self, node: WhileLoop):
        self.visit_expr(node.condition)
        self.enter_scope("while", is_loop=True)
        for stmt in node.body:
            self.visit_stmt(stmt)
        self.exit_scope()

    def visit_RepeatLoop(self, node: RepeatLoop):
        self.visit_expr(node.count)
        self.enter_scope("repeat", is_loop=True)
        for stmt in node.body:
            self.visit_stmt(stmt)
        self.exit_scope()

    def visit_FunctionDef(self, node: FunctionDef):
        self.enter_scope(node.name, is_function=True, is_loop=False)
        for _, param_name in node.params:
            self.current_scope.declare(param_name)
        for stmt in node.body:
            self.visit_stmt(stmt)
        self.exit_scope()

    def visit_TryBlock(self, node: TryBlock):
        self.enter_scope("try", is_loop=self.current_scope.is_loop)
        for stmt in node.try_body:
            self.visit_stmt(stmt)
        self.exit_scope()

        self.enter_scope("on_failure", is_loop=self.current_scope.is_loop)
        if node.failure_name:
            self.current_scope.declare(node.failure_name)
        for stmt in node.failure_body:
            self.visit_stmt(stmt)
        self.exit_scope()

    # --- Expression Visitors ---

    def visit_expr(self, expr: Expr):
        if isinstance(expr, Identifier):
            name = expr.name
            if not self.current_scope.is_declared(name) and name not in self.builtin_names and name not in self.functions:
                suggestion = self.get_suggestion(name)
                sugg_msg = f" Did you mean '{suggestion}'?" if suggestion else ""
                raise CompileError(
                    f"Line {expr.line}: I don't know a variable called '{name}'.{sugg_msg}",
                    line=expr.line, column=expr.column, code="P301"
                )
        elif isinstance(expr, BinaryOp):
            self.visit_expr(expr.left)
            self.visit_expr(expr.right)
        elif isinstance(expr, UnaryOp):
            self.visit_expr(expr.operand)
        elif isinstance(expr, Between):
            self.visit_expr(expr.expr)
            self.visit_expr(expr.low)
            self.visit_expr(expr.high)
        elif isinstance(expr, (IsEmpty, IsNothing)):
            self.visit_expr(expr.expr)
        elif isinstance(expr, Call):
            # Check function arity if calling a known PLAN function
            if isinstance(expr.callee, Identifier):
                fn_name = expr.callee.name
                if fn_name in self.functions:
                    f_info = self.functions[fn_name]
                    actual = len(expr.args) + len(expr.kwargs)
                    if actual != f_info.param_count:
                        raise CompileError(
                            f"Line {expr.line}: '{fn_name}' needs {f_info.param_count} values but was given {actual}.",
                            line=expr.line, column=expr.column, code="P308"
                        )
                elif not self.current_scope.is_declared(fn_name) and fn_name not in self.builtin_names:
                    suggestion = self.get_suggestion(fn_name)
                    sugg_msg = f" Did you mean '{suggestion}'?" if suggestion else ""
                    raise CompileError(
                        f"Line {expr.line}: I don't know a function called '{fn_name}'.{sugg_msg}",
                        line=expr.line, column=expr.column, code="P301"
                    )
            else:
                self.visit_expr(expr.callee)

            for arg in expr.args:
                self.visit_expr(arg)
            for kwarg_val in expr.kwargs.values():
                self.visit_expr(kwarg_val)

        elif isinstance(expr, MemberAccess):
            self.visit_expr(expr.target)
        elif isinstance(expr, Index):
            self.visit_expr(expr.target)
            self.visit_expr(expr.index)
        elif isinstance(expr, (FirstItem, LastItem)):
            self.visit_expr(expr.target)
        elif isinstance(expr, EntryIndex):
            self.visit_expr(expr.target)
            self.visit_expr(expr.key)
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self.visit_expr(item)
        elif isinstance(expr, Phrase):
            for arg in expr.args:
                self.visit_expr(arg)

    def get_suggestion(self, name: str) -> Optional[str]:
        visible = list(self.current_scope.all_visible_names() | set(self.functions.keys()) | self.builtin_names)
        matches = difflib.get_close_matches(name, visible, n=1, cutoff=0.6)
        return matches[0] if matches else None
