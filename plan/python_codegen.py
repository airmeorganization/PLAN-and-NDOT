import ast as pyast
from plan.ast_nodes import *

class Codegen:
    def __init__(self):
        pass

    def generate(self, program: Program) -> pyast.Module:
        body = [self.visit(stmt) for stmt in program.statements]
        
        # Always inject the runtime module import
        # import plan.runtime as plan_rt
        import_stmt = pyast.Import(names=[pyast.alias(name='plan.runtime', asname='plan_rt')], lineno=1, col_offset=0)
        body.insert(0, import_stmt)
        
        return pyast.Module(body=body, type_ignores=[])

    def visit(self, node: ASTNode) -> pyast.AST:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode) -> pyast.AST:
        raise NotImplementedError(f"No visit_{type(node).__name__} method")

    # --- Statements ---
    
    def visit_Declare(self, node: Declare) -> pyast.stmt:
        target = pyast.Name(id=node.name, ctx=pyast.Store(), lineno=node.line, col_offset=node.column)
        value = self.visit(node.value)
        return pyast.Assign(targets=[target], value=value, lineno=node.line, col_offset=node.column)

    def visit_SetStmt(self, node: SetStmt) -> pyast.stmt:
        target = self.visit(node.target)
        # convert load context to store context
        target.ctx = pyast.Store()
        value = self.visit(node.value)
        return pyast.Assign(targets=[target], value=value, lineno=node.line, col_offset=node.column)

    def visit_Show(self, node: Show) -> pyast.stmt:
        args = [self.visit(e) for e in node.exprs]
        func = pyast.Name(id='print', ctx=pyast.Load(), lineno=node.line, col_offset=node.column)
        # If multiple exprs joined by 'followed by', we use sep=""
        kwargs = []
        if len(args) > 1:
            kwargs.append(pyast.keyword(arg='sep', value=pyast.Constant(value="")))
            
        call = pyast.Call(func=func, args=args, keywords=kwargs, lineno=node.line, col_offset=node.column)
        return pyast.Expr(value=call, lineno=node.line, col_offset=node.column)

    def visit_PythonRaw(self, node: PythonRaw) -> pyast.stmt:
        # Parse the raw code and return its body
        # ast.parse returns a Module, we just extract its body
        parsed_module = pyast.parse(node.code)
        # return a list of statements (ast.unparse handles flattening if returned in body)
        # However, visit() normally returns a single AST node.
        # To embed multiple statements, we can wrap them in an ast.If(True, body, [])
        # But wait, it's better to just return the first statement, or we need visit to return a list.
        # For simplicity in this v0.1 parser, we'll wrap it in `if True:`
        if_node = pyast.If(test=pyast.Constant(value=True), body=parsed_module.body, orelse=[], lineno=node.line, col_offset=node.column)
        return if_node

    # --- Expressions ---

    def visit_Literal(self, node: Literal) -> pyast.expr:
        return pyast.Constant(value=node.value, lineno=node.line, col_offset=node.column)

    def visit_Identifier(self, node: Identifier) -> pyast.expr:
        return pyast.Name(id=node.name, ctx=pyast.Load(), lineno=node.line, col_offset=node.column)
