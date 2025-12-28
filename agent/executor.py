import io
import contextlib
import builtins
from typing import Dict, Any

from agent.models import ToolResult
from agent.safety import validate_code, SAFE_MODULES
from agent.sanitize import sanitize_locals

# Create a restricted version of builtins
SAFE_BUILTINS = {
    name: getattr(builtins, name)
    for name in [
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes", "callable",
        "chr", "complex", "dict", "divmod", "enumerate", "filter", "float", "format",
        "frozenset", "getattr", "hasattr", "hash", "help", "hex", "id", "int", "isinstance",
        "issubclass", "iter", "len", "list", "map", "max", "min", "next", "object", "oct",
        "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set",
        "slice", "sorted", "str", "sum", "tuple", "type", "zip"
    ]
}


def get_safe_globals() -> Dict[str, Any]:
    return {"__builtins__": SAFE_BUILTINS}

def run_code_capture(code: str, initial_locals: Dict[str, Any] = None) -> ToolResult:
    errors = validate_code(code)
    if errors:
        return ToolResult(
            stdout="",
            error=f"Security Violations:\n" + "\n".join(errors),
            locals={}
        )

    stdout = io.StringIO()
    locals_dict = initial_locals.copy() if initial_locals else {}
    
    safe_globals = get_safe_globals()

    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, safe_globals, locals_dict)
        
        return ToolResult(
            stdout=stdout.getvalue(),
            error=None,
            locals=sanitize_locals(locals_dict)
        )
    except Exception as e:
        return ToolResult(
            stdout=stdout.getvalue(),
            error=str(e),
            locals={}
        )


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_code_capture",
            "description": "Execute Python code and capture stdout and local variables. Sandbox restricted: no os, sys, subprocess.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"}
                },
                "required": ["code"],
                "additionalProperties": False
            }
        }
    }
]
