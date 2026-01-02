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
        "__import__", "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes", "callable",
        "chr", "complex", "dict", "divmod", "enumerate", "filter", "float", "format",
        "frozenset", "getattr", "hasattr", "hash", "help", "hex", "id", "int", "isinstance",
        "issubclass", "iter", "len", "list", "map", "max", "min", "next", "object", "oct",
        "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set",
        "slice", "sorted", "str", "sum", "tuple", "type", "zip"
    ]
}


def get_safe_globals() -> Dict[str, Any]:
    return {"__builtins__": SAFE_BUILTINS}

import os
import tempfile
import glob

# Configure Matplotlib backend to Agg to prevent GUI errors
try:
    import matplotlib
    matplotlib.use('Agg')
except ImportError:
    pass

def run_code_capture(code: str, initial_locals: Dict[str, Any] = None) -> ToolResult:
    errors = validate_code(code)
    if errors:
        return ToolResult(
            stdout="",
            error=f"Security Violations:\n" + "\n".join(errors),
            locals={},
            artifacts=[]
        )

    stdout = io.StringIO()
    locals_dict = initial_locals.copy() if initial_locals else {}
    
    # Create a temporary directory for artifacts
    artifact_dir = tempfile.mkdtemp(prefix="agent_artifacts_")
    locals_dict["output_dir"] = artifact_dir
    
    safe_globals = get_safe_globals()

    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, safe_globals, locals_dict)
        
        # Scan for artifacts
        artifacts = []
        if os.path.exists(artifact_dir):
            for file_path in glob.glob(os.path.join(artifact_dir, "*")):
                if os.path.isfile(file_path):
                    artifacts.append(file_path)
        
        # Sanitize locals might remove output_dir, but that's fine
        return ToolResult(
            stdout=stdout.getvalue(),
            error=None,
            locals=sanitize_locals(locals_dict),
            artifacts=artifacts
        )
    except Exception as e:
        return ToolResult(
            stdout=stdout.getvalue(),
            error=str(e),
            locals={},
            artifacts=[]
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
