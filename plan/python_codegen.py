import ast as pyast
from typing import List, Set, Any, Optional
from plan.ast_nodes import *
from plan.phrases import PHRASE_REGISTRY

PLAN_TO_PYTHON_TYPES = {
    'number': 'float',
    'float': 'float',
    'whole number': 'int',
    'whole_number': 'int',
    'int': 'int',
    'text': 'str',
    'str': 'str',
    'string': 'str',
    'list': 'list',
    'dictionary': 'dict',
    'dict': 'dict',
    'flag': 'bool',
    'bool': 'bool',
    'boolean': 'bool',
}

def to_python_type(type_name: Optional[str]) -> Optional[str]:
    if not type_name:
        return None
    cleaned = type_name.strip().lower()
    return PLAN_TO_PYTHON_TYPES.get(cleaned, cleaned)

class Codegen:
    """PLAN to Python AST Generator."""

    def __init__(self):
        self.needed_imports: Set[str] = set()

    def generate(self, program: Program) -> pyast.Module:
        self.needed_imports = set()

        # Split statements into hoisted function definitions and regular statements
        fn_defs = []
        regular_stmts = []

        for stmt in program.statements:
            if isinstance(stmt, FunctionDef):
                fn_defs.append(self.visit_stmt(stmt))
            elif isinstance(stmt, PythonRaw):
                # Raw python might have multiple statements
                raw_ast = pyast.parse(stmt.code)
                regular_stmts.extend(raw_ast.body)
            else:
                s = self.visit_stmt(stmt)
                if s:
                    regular_stmts.append(s)

        # Injected module header:
        # import plan.runtime as plan_rt
        header_stmts: List[pyast.stmt] = [
            pyast.Import(names=[pyast.alias(name='plan.runtime', asname='plan_rt')], lineno=1, col_offset=0)
        ]

        # Additional required standard library imports discovered from phrases
        for mod in sorted(self.needed_imports):
            header_stmts.append(pyast.Import(names=[pyast.alias(name=mod, asname=None)], lineno=1, col_offset=0))

        all_body = header_stmts + fn_defs + regular_stmts
        return pyast.Module(body=all_body, type_ignores=[])

    def visit_stmt(self, node: Statement) -> pyast.stmt:
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if not method:
            raise NotImplementedError(f"Codegen missing statement visitor for {type(node).__name__}")
        return method(node)

    def visit_expr(self, node: Expr) -> pyast.expr:
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if not method:
            raise NotImplementedError(f"Codegen missing expression visitor for {type(node).__name__}")
        return method(node)

    # --- Statements ---

    def visit_Declare(self, node: Declare) -> pyast.stmt:
        target = pyast.Name(id=node.name, ctx=pyast.Store(), lineno=node.line, col_offset=node.column)
        value = self.visit_expr(node.value)
        return pyast.Assign(targets=[target], value=value, lineno=node.line, col_offset=node.column)

    def visit_SetStmt(self, node: SetStmt) -> pyast.stmt:
        value = self.visit_expr(node.value)
        target_node = node.target

        if isinstance(target_node, Identifier):
            target = pyast.Name(id=target_node.name, ctx=pyast.Store(), lineno=node.line, col_offset=node.column)
            return pyast.Assign(targets=[target], value=value, lineno=node.line, col_offset=node.column)

        elif isinstance(target_node, Index):
            # item n of target = value -> plan_rt.set_item(target, n, value, line)
            call_set = pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='plan_rt', ctx=pyast.Load(), lineno=node.line, col_offset=node.column), attr='set_item', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
                args=[self.visit_expr(target_node.target), self.visit_expr(target_node.index), value, pyast.Constant(value=node.line, lineno=node.line, col_offset=node.column)],
                keywords=[],
                lineno=node.line, col_offset=node.column
            )
            return pyast.Expr(value=call_set, lineno=node.line, col_offset=node.column)

        elif isinstance(target_node, FirstItem):
            sub = pyast.Subscript(
                value=self.visit_expr(target_node.target),
                slice=pyast.Constant(value=0, lineno=node.line, col_offset=node.column),
                ctx=pyast.Store(),
                lineno=node.line, col_offset=node.column
            )
            return pyast.Assign(targets=[sub], value=value, lineno=node.line, col_offset=node.column)

        elif isinstance(target_node, LastItem):
            sub = pyast.Subscript(
                value=self.visit_expr(target_node.target),
                slice=pyast.Constant(value=-1, lineno=node.line, col_offset=node.column),
                ctx=pyast.Store(),
                lineno=node.line, col_offset=node.column
            )
            return pyast.Assign(targets=[sub], value=value, lineno=node.line, col_offset=node.column)

        elif isinstance(target_node, EntryIndex):
            sub = pyast.Subscript(
                value=self.visit_expr(target_node.target),
                slice=self.visit_expr(target_node.key),
                ctx=pyast.Store(),
                lineno=node.line, col_offset=node.column
            )
            return pyast.Assign(targets=[sub], value=value, lineno=node.line, col_offset=node.column)

        elif isinstance(target_node, MemberAccess):
            attr = pyast.Attribute(
                value=self.visit_expr(target_node.target),
                attr=target_node.member,
                ctx=pyast.Store(),
                lineno=node.line, col_offset=node.column
            )
            return pyast.Assign(targets=[attr], value=value, lineno=node.line, col_offset=node.column)

        raise NotImplementedError(f"Unsupported target in SetStmt: {type(target_node)}")

    def visit_ModifyStmt(self, node: ModifyStmt) -> pyast.stmt:
        target = self.visit_expr(node.target)
        val = self.visit_expr(node.value)

        if node.op == '+':
            # target += val
            target.ctx = pyast.Store()
            return pyast.AugAssign(target=target, op=pyast.Add(), value=val, lineno=node.line, col_offset=node.column)
        elif node.op == '-':
            # target -= val
            target.ctx = pyast.Store()
            return pyast.AugAssign(target=target, op=pyast.Sub(), value=val, lineno=node.line, col_offset=node.column)
        elif node.op == 'append':
            # target.append(val)
            call = pyast.Call(
                func=pyast.Attribute(value=target, attr='append', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
                args=[val], keywords=[], lineno=node.line, col_offset=node.column
            )
            return pyast.Expr(value=call, lineno=node.line, col_offset=node.column)
        elif node.op == 'remove':
            # target.remove(val)
            call = pyast.Call(
                func=pyast.Attribute(value=target, attr='remove', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
                args=[val], keywords=[], lineno=node.line, col_offset=node.column
            )
            return pyast.Expr(value=call, lineno=node.line, col_offset=node.column)

        raise NotImplementedError(f"Unknown modify op: {node.op}")

    def visit_Show(self, node: Show) -> pyast.stmt:
        args = [self.visit_expr(e) for e in node.exprs]
        kwargs = []
        if node.followed_by:
            kwargs.append(pyast.keyword(arg='sep', value=pyast.Constant(value="")))
        call = pyast.Call(
            func=pyast.Name(id='print', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
            args=args, keywords=kwargs, lineno=node.line, col_offset=node.column
        )
        return pyast.Expr(value=call, lineno=node.line, col_offset=node.column)

    def visit_Ask(self, node: Ask) -> pyast.stmt:
        prompt = self.visit_expr(node.prompt)
        input_call = pyast.Call(
            func=pyast.Name(id='input', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
            args=[prompt], keywords=[], lineno=node.line, col_offset=node.column
        )
        if node.kind == 'number':
            val_expr = pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='plan_rt', ctx=pyast.Load(), lineno=node.line, col_offset=node.column), attr='to_number', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
                args=[input_call], keywords=[], lineno=node.line, col_offset=node.column
            )
        elif node.kind == 'whole_number':
            val_expr = pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='plan_rt', ctx=pyast.Load(), lineno=node.line, col_offset=node.column), attr='to_whole_number', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
                args=[input_call], keywords=[], lineno=node.line, col_offset=node.column
            )
        else:
            val_expr = input_call

        target = pyast.Name(id=node.target, ctx=pyast.Store(), lineno=node.line, col_offset=node.column)
        return pyast.Assign(targets=[target], value=val_expr, lineno=node.line, col_offset=node.column)

    def visit_UseModule(self, node: UseModule) -> pyast.stmt:
        return pyast.Import(
            names=[pyast.alias(name=node.module, asname=node.alias)],
            lineno=node.line, col_offset=node.column
        )

    def visit_UseFromModule(self, node: UseFromModule) -> pyast.stmt:
        names = [pyast.alias(name=n, asname=None) for n in node.names]
        return pyast.ImportFrom(
            module=node.module, names=names, level=0,
            lineno=node.line, col_offset=node.column
        )

    def visit_UseShared(self, node: UseShared) -> pyast.stmt:
        return pyast.Global(names=[node.name], lineno=node.line, col_offset=node.column)

    def visit_Return(self, node: Return) -> pyast.stmt:
        val = self.visit_expr(node.value) if node.value else None
        return pyast.Return(value=val, lineno=node.line, col_offset=node.column)

    def visit_CallStmt(self, node: CallStmt) -> pyast.stmt:
        call_expr = self.visit_expr(node.call)
        return pyast.Expr(value=call_expr, lineno=node.line, col_offset=node.column)

    def visit_Stop(self, node: Stop) -> pyast.stmt:
        if node.target == 'loop':
            return pyast.Break(lineno=node.line, col_offset=node.column)
        else:
            return pyast.Raise(
                exc=pyast.Call(func=pyast.Name(id='SystemExit', ctx=pyast.Load(), lineno=node.line, col_offset=node.column), args=[], keywords=[], lineno=node.line, col_offset=node.column),
                cause=None, lineno=node.line, col_offset=node.column
            )

    def visit_Skip(self, node: Skip) -> pyast.stmt:
        return pyast.Continue(lineno=node.line, col_offset=node.column)

    # --- Blocks ---

    def visit_WhenBlock(self, node: WhenBlock) -> pyast.stmt:
        def build_if_chain(cases: List[WhenCase], otherwise: Optional[List[Statement]], idx: int) -> List[pyast.stmt]:
            if idx >= len(cases):
                return [self.visit_stmt(s) for s in otherwise] if otherwise else []
            case = cases[idx]
            test = self.visit_expr(case.condition)
            body = [self.visit_stmt(s) for s in case.body] or [pyast.Pass()]
            orelse = build_if_chain(cases, otherwise, idx + 1)
            return [pyast.If(test=test, body=body, orelse=orelse, lineno=node.line, col_offset=node.column)]

        chain = build_if_chain(node.cases, node.otherwise_body, 0)
        return chain[0] if chain else pyast.Pass(lineno=node.line, col_offset=node.column)

    def visit_ForRange(self, node: ForRange) -> pyast.stmt:
        var = pyast.Name(id=node.var_name, ctx=pyast.Store(), lineno=node.line, col_offset=node.column)
        start = self.visit_expr(node.start)
        end = self.visit_expr(node.end)

        # PLAN bounds are inclusive: adjusted by the step's sign (spec §6.1)
        if node.step:
            step = self.visit_expr(node.step)
            is_statically_negative = False
            is_statically_positive = False

            if isinstance(node.step, Literal) and isinstance(node.step.value, (int, float)):
                if node.step.value < 0:
                    is_statically_negative = True
                elif node.step.value > 0:
                    is_statically_positive = True
            elif isinstance(node.step, UnaryOp) and node.step.op == '-':
                if isinstance(node.step.operand, Literal) and isinstance(node.step.operand.value, (int, float)):
                    if node.step.operand.value > 0:
                        is_statically_negative = True

            if is_statically_negative:
                # 10 to 1 in steps of -1 -> range(10, 1 - 1, -1)
                adj_end = pyast.BinOp(left=end, op=pyast.Sub(), right=pyast.Constant(value=1), lineno=node.line, col_offset=node.column)
            elif is_statically_positive:
                # 1 to 10 in steps of 2 -> range(1, 10 + 1, 2)
                adj_end = pyast.BinOp(left=end, op=pyast.Add(), right=pyast.Constant(value=1), lineno=node.line, col_offset=node.column)
            else:
                # Dynamic step: end + (1 if step > 0 else -1)
                step_sign = pyast.IfExp(
                    test=pyast.Compare(left=step, ops=[pyast.Gt()], comparators=[pyast.Constant(value=0)], lineno=node.line, col_offset=node.column),
                    body=pyast.Constant(value=1),
                    orelse=pyast.Constant(value=-1),
                    lineno=node.line, col_offset=node.column
                )
                adj_end = pyast.BinOp(left=end, op=pyast.Add(), right=step_sign, lineno=node.line, col_offset=node.column)

            range_call = pyast.Call(
                func=pyast.Name(id='range', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
                args=[start, adj_end, step], keywords=[], lineno=node.line, col_offset=node.column
            )
        else:
            # Default step is +1: range(start, end + 1)
            adj_end = pyast.BinOp(left=end, op=pyast.Add(), right=pyast.Constant(value=1), lineno=node.line, col_offset=node.column)
            range_call = pyast.Call(
                func=pyast.Name(id='range', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
                args=[start, adj_end], keywords=[], lineno=node.line, col_offset=node.column
            )

        body = [self.visit_stmt(s) for s in node.body] or [pyast.Pass()]
        return pyast.For(target=var, iter=range_call, body=body, orelse=[], lineno=node.line, col_offset=node.column)

    def visit_ForEach(self, node: ForEach) -> pyast.stmt:
        var = pyast.Name(id=node.var_name, ctx=pyast.Store(), lineno=node.line, col_offset=node.column)
        iter_expr = self.visit_expr(node.iterable)
        body = [self.visit_stmt(s) for s in node.body] or [pyast.Pass()]
        return pyast.For(target=var, iter=iter_expr, body=body, orelse=[], lineno=node.line, col_offset=node.column)

    def visit_WhileLoop(self, node: WhileLoop) -> pyast.stmt:
        test = self.visit_expr(node.condition)
        body = [self.visit_stmt(s) for s in node.body] or [pyast.Pass()]
        return pyast.While(test=test, body=body, orelse=[], lineno=node.line, col_offset=node.column)

    def visit_RepeatLoop(self, node: RepeatLoop) -> pyast.stmt:
        var = pyast.Name(id='_plan_i', ctx=pyast.Store(), lineno=node.line, col_offset=node.column)
        count = self.visit_expr(node.count)
        range_call = pyast.Call(
            func=pyast.Name(id='range', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
            args=[count], keywords=[], lineno=node.line, col_offset=node.column
        )
        body = [self.visit_stmt(s) for s in node.body] or [pyast.Pass()]
        return pyast.For(target=var, iter=range_call, body=body, orelse=[], lineno=node.line, col_offset=node.column)

    def visit_FunctionDef(self, node: FunctionDef) -> pyast.stmt:
        args = []
        for param_type, param_name in node.params:
            py_type = to_python_type(param_type)
            ann = pyast.Name(id=py_type, ctx=pyast.Load(), lineno=node.line, col_offset=node.column) if py_type else None
            args.append(pyast.arg(arg=param_name, annotation=ann, lineno=node.line, col_offset=node.column))

        arguments = pyast.arguments(
            posonlyargs=[], args=args, vararg=None, kwonlyargs=[],
            kw_defaults=[], kwarg=None, defaults=[]
        )
        py_ret_type = to_python_type(node.return_type)
        ret_ann = pyast.Name(id=py_ret_type, ctx=pyast.Load(), lineno=node.line, col_offset=node.column) if py_ret_type else None
        body = [self.visit_stmt(s) for s in node.body] or [pyast.Pass()]
        return pyast.FunctionDef(
            name=node.name, args=arguments, body=body, decorator_list=[],
            returns=ret_ann, lineno=node.line, col_offset=node.column
        )

    def visit_TryBlock(self, node: TryBlock) -> pyast.stmt:
        body = [self.visit_stmt(s) for s in node.try_body] or [pyast.Pass()]
        handler = pyast.ExceptHandler(
            type=pyast.Name(id='Exception', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
            name=node.failure_name,
            body=[self.visit_stmt(s) for s in node.failure_body] or [pyast.Pass()],
            lineno=node.line, col_offset=node.column
        )
        return pyast.Try(body=body, handlers=[handler], orelse=[], finalbody=[], lineno=node.line, col_offset=node.column)

    # --- Expressions ---

    def visit_Literal(self, node: Literal) -> pyast.expr:
        return pyast.Constant(value=node.value, lineno=node.line, col_offset=node.column)

    def visit_Identifier(self, node: Identifier) -> pyast.expr:
        return pyast.Name(id=node.name, ctx=pyast.Load(), lineno=node.line, col_offset=node.column)

    def visit_BinaryOp(self, node: BinaryOp) -> pyast.expr:
        left = self.visit_expr(node.left)
        right = self.visit_expr(node.right)

        op_map = {
            '+': (pyast.BinOp, pyast.Add),
            '-': (pyast.BinOp, pyast.Sub),
            '*': (pyast.BinOp, pyast.Mult),
            '/': (pyast.BinOp, pyast.Div),
            '%': (pyast.BinOp, pyast.Mod),
            '**': (pyast.BinOp, pyast.Pow),
            '==': (pyast.Compare, pyast.Eq),
            '!=': (pyast.Compare, pyast.NotEq),
            '<': (pyast.Compare, pyast.Lt),
            '<=': (pyast.Compare, pyast.LtE),
            '>': (pyast.Compare, pyast.Gt),
            '>=': (pyast.Compare, pyast.GtE),
            'in': (pyast.Compare, pyast.In),
            'not in': (pyast.Compare, pyast.NotIn),
            'and': (pyast.BoolOp, pyast.And),
            'or': (pyast.BoolOp, pyast.Or),
        }

        entry = op_map.get(node.op)
        if not entry:
            raise NotImplementedError(f"Unsupported binary operator: {node.op}")

        cls, op_cls = entry
        if cls is pyast.BinOp:
            return pyast.BinOp(left=left, op=op_cls(), right=right, lineno=node.line, col_offset=node.column)
        elif cls is pyast.Compare:
            return pyast.Compare(left=left, ops=[op_cls()], comparators=[right], lineno=node.line, col_offset=node.column)
        elif cls is pyast.BoolOp:
            return pyast.BoolOp(op=op_cls(), values=[left, right], lineno=node.line, col_offset=node.column)

    def visit_UnaryOp(self, node: UnaryOp) -> pyast.expr:
        opnd = self.visit_expr(node.operand)
        if node.op == '-':
            return pyast.UnaryOp(op=pyast.USub(), operand=opnd, lineno=node.line, col_offset=node.column)
        elif node.op == 'not':
            return pyast.UnaryOp(op=pyast.Not(), operand=opnd, lineno=node.line, col_offset=node.column)
        raise NotImplementedError(f"Unsupported unary operator: {node.op}")

    def visit_Between(self, node: Between) -> pyast.expr:
        val = self.visit_expr(node.expr)
        low = self.visit_expr(node.low)
        high = self.visit_expr(node.high)
        # low <= val <= high
        comp = pyast.Compare(left=low, ops=[pyast.LtE(), pyast.LtE()], comparators=[val, high], lineno=node.line, col_offset=node.column)
        if node.negated:
            return pyast.UnaryOp(op=pyast.Not(), operand=comp, lineno=node.line, col_offset=node.column)
        return comp

    def visit_IsEmpty(self, node: IsEmpty) -> pyast.expr:
        val = self.visit_expr(node.expr)
        len_call = pyast.Call(func=pyast.Name(id='len', ctx=pyast.Load()), args=[val], keywords=[], lineno=node.line, col_offset=node.column)
        op = pyast.NotEq() if node.negated else pyast.Eq()
        return pyast.Compare(left=len_call, ops=[op], comparators=[pyast.Constant(value=0)], lineno=node.line, col_offset=node.column)

    def visit_IsNothing(self, node: IsNothing) -> pyast.expr:
        val = self.visit_expr(node.expr)
        op = pyast.IsNot() if node.negated else pyast.Is()
        return pyast.Compare(left=val, ops=[op], comparators=[pyast.Constant(value=None)], lineno=node.line, col_offset=node.column)

    def visit_Index(self, node: Index) -> pyast.expr:
        # plan_rt.item(target, index, line)
        target = self.visit_expr(node.target)
        idx = self.visit_expr(node.index)
        return pyast.Call(
            func=pyast.Attribute(value=pyast.Name(id='plan_rt', ctx=pyast.Load(), lineno=node.line, col_offset=node.column), attr='item', ctx=pyast.Load(), lineno=node.line, col_offset=node.column),
            args=[target, idx, pyast.Constant(value=node.line, lineno=node.line, col_offset=node.column)],
            keywords=[], lineno=node.line, col_offset=node.column
        )

    def visit_FirstItem(self, node: FirstItem) -> pyast.expr:
        target = self.visit_expr(node.target)
        return pyast.Subscript(value=target, slice=pyast.Constant(value=0), ctx=pyast.Load(), lineno=node.line, col_offset=node.column)

    def visit_LastItem(self, node: LastItem) -> pyast.expr:
        target = self.visit_expr(node.target)
        return pyast.Subscript(value=target, slice=pyast.Constant(value=-1), ctx=pyast.Load(), lineno=node.line, col_offset=node.column)

    def visit_EntryIndex(self, node: EntryIndex) -> pyast.expr:
        target = self.visit_expr(node.target)
        key = self.visit_expr(node.key)
        return pyast.Subscript(value=target, slice=key, ctx=pyast.Load(), lineno=node.line, col_offset=node.column)

    def visit_MemberAccess(self, node: MemberAccess) -> pyast.expr:
        target = self.visit_expr(node.target)
        return pyast.Attribute(value=target, attr=node.member, ctx=pyast.Load(), lineno=node.line, col_offset=node.column)

    def visit_ListLiteral(self, node: ListLiteral) -> pyast.expr:
        elts = [self.visit_expr(e) for e in node.items]
        return pyast.List(elts=elts, ctx=pyast.Load(), lineno=node.line, col_offset=node.column)

    def visit_DictLiteral(self, node: DictLiteral) -> pyast.expr:
        return pyast.Dict(keys=[], values=[], lineno=node.line, col_offset=node.column)

    def visit_Call(self, node: Call) -> pyast.expr:
        callee = self.visit_expr(node.callee)
        args = [self.visit_expr(a) for a in node.args]
        keywords = [pyast.keyword(arg=k, value=self.visit_expr(v)) for k, v in node.kwargs.items()]
        return pyast.Call(func=callee, args=args, keywords=keywords, lineno=node.line, col_offset=node.column)

    def visit_Phrase(self, node: Phrase) -> pyast.expr:
        # Check phrase registry for required imports
        pdef = PHRASE_REGISTRY.get(node.name)
        if pdef and pdef.auto_imports:
            for imp in pdef.auto_imports:
                self.needed_imports.add(imp)

        args = [self.visit_expr(a) for a in node.args]
        line = node.line
        col = node.column

        if node.name == 'square_root':
            # math.sqrt(args[0])
            return pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='math', ctx=pyast.Load()), attr='sqrt', ctx=pyast.Load()),
                args=args, keywords=[], lineno=line, col_offset=col
            )
        elif node.name == 'absolute_value':
            return pyast.Call(func=pyast.Name(id='abs', ctx=pyast.Load()), args=args, keywords=[], lineno=line, col_offset=col)
        elif node.name == 'length_of':
            return pyast.Call(func=pyast.Name(id='len', ctx=pyast.Load()), args=args, keywords=[], lineno=line, col_offset=col)
        elif node.name == 'sum_of':
            return pyast.Call(func=pyast.Name(id='sum', ctx=pyast.Load()), args=args, keywords=[], lineno=line, col_offset=col)
        elif node.name == 'largest_of':
            return pyast.Call(func=pyast.Name(id='max', ctx=pyast.Load()), args=args, keywords=[], lineno=line, col_offset=col)
        elif node.name == 'smallest_of':
            return pyast.Call(func=pyast.Name(id='min', ctx=pyast.Load()), args=args, keywords=[], lineno=line, col_offset=col)
        elif node.name == 'average_of':
            return pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='statistics', ctx=pyast.Load()), attr='mean', ctx=pyast.Load()),
                args=args, keywords=[], lineno=line, col_offset=col
            )
        elif node.name == 'rounded':
            return pyast.Call(func=pyast.Name(id='round', ctx=pyast.Load()), args=args, keywords=[], lineno=line, col_offset=col)
        elif node.name == 'as_text':
            return pyast.Call(func=pyast.Name(id='str', ctx=pyast.Load()), args=args, keywords=[], lineno=line, col_offset=col)
        elif node.name == 'as_number':
            return pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='plan_rt', ctx=pyast.Load()), attr='to_number', ctx=pyast.Load()),
                args=args, keywords=[], lineno=line, col_offset=col
            )
        elif node.name == 'as_whole_number':
            return pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='plan_rt', ctx=pyast.Load()), attr='to_whole_number', ctx=pyast.Load()),
                args=args, keywords=[], lineno=line, col_offset=col
            )
        elif node.name == 'uppercase':
            return pyast.Call(func=pyast.Attribute(value=args[0], attr='upper', ctx=pyast.Load()), args=[], keywords=[], lineno=line, col_offset=col)
        elif node.name == 'lowercase':
            return pyast.Call(func=pyast.Attribute(value=args[0], attr='lower', ctx=pyast.Load()), args=[], keywords=[], lineno=line, col_offset=col)
        elif node.name == 'sorted':
            return pyast.Call(func=pyast.Name(id='sorted', ctx=pyast.Load()), args=[args[0]], keywords=[], lineno=line, col_offset=col)
        elif node.name == 'reversed':
            rev_call = pyast.Call(func=pyast.Name(id='reversed', ctx=pyast.Load()), args=[args[0]], keywords=[], lineno=line, col_offset=col)
            return pyast.Call(func=pyast.Name(id='list', ctx=pyast.Load()), args=[rev_call], keywords=[], lineno=line, col_offset=col)
        elif node.name == 'split_by':
            return pyast.Call(func=pyast.Attribute(value=args[0], attr='split', ctx=pyast.Load()), args=[args[1]], keywords=[], lineno=line, col_offset=col)
        elif node.name == 'joined_with':
            # sep.join(str(i) for i in x)
            gen = pyast.GeneratorExp(
                elt=pyast.Call(func=pyast.Name(id='str', ctx=pyast.Load()), args=[pyast.Name(id='_item', ctx=pyast.Load())], keywords=[]),
                generators=[pyast.comprehension(target=pyast.Name(id='_item', ctx=pyast.Store()), iter=args[0], ifs=[], is_async=0)],
                lineno=line, col_offset=col
            )
            return pyast.Call(func=pyast.Attribute(value=args[1], attr='join', ctx=pyast.Load()), args=[gen], keywords=[], lineno=line, col_offset=col)
        elif node.name == 'random_number':
            return pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='random', ctx=pyast.Load()), attr='randint', ctx=pyast.Load()),
                args=args, keywords=[], lineno=line, col_offset=col
            )
        elif node.name == 'random_item':
            return pyast.Call(
                func=pyast.Attribute(value=pyast.Name(id='random', ctx=pyast.Load()), attr='choice', ctx=pyast.Load()),
                args=args, keywords=[], lineno=line, col_offset=col
            )
        elif node.name == 'current_time':
            return pyast.Call(
                func=pyast.Attribute(value=pyast.Attribute(value=pyast.Name(id='datetime', ctx=pyast.Load()), attr='datetime', ctx=pyast.Load()), attr='now', ctx=pyast.Load()),
                args=[], keywords=[], lineno=line, col_offset=col
            )

        raise NotImplementedError(f"Phrase '{node.name}' has no codegen lowering.")
