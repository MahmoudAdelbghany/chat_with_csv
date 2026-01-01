
import ast

SAFE_MODULES = {"math", "datetime", "pandas", "numpy", "matplotlib", "plotly", "seaborn", "ydata_profiling", "scipy"}
UNSAFE_BUILTINS = {
    "__import__", "open", "exec", "eval", "compile", 
    "globals", "locals", "super", "input", "exit", "quit"
}

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split('.')[0] not in SAFE_MODULES:
                self.errors.append(f"Import of '{alias.name}' is not allowed")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split('.')[0] not in SAFE_MODULES:
            self.errors.append(f"Import from '{node.module}' is not allowed")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in UNSAFE_BUILTINS:
                self.errors.append(f"Call to '{node.func.id}' is not allowed")
        self.generic_visit(node)

def validate_code(code: str):
    """
    Parses code into AST and checks for unsafe operations.
    Returns a list of error strings. If list is empty, code is considered safe(r).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"SyntaxError: {str(e)}"]

    visitor = SecurityVisitor()
    visitor.visit(tree)
    return visitor.errors
