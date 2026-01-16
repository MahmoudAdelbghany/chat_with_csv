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
from core.logger import logger

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
    
    # Use TemporaryDirectory context manager for automatic cleanup
    with tempfile.TemporaryDirectory(prefix="agent_artifacts_") as artifact_dir:
        locals_dict["output_dir"] = artifact_dir
        
        safe_globals = get_safe_globals()

        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, safe_globals, locals_dict)
            
            # Scan for artifacts and copy them to a persistent location
            # before the temp directory is cleaned up
            artifacts = []
            persistent_dir = tempfile.mkdtemp(prefix="agent_artifacts_persist_")
            
            # Log artifact scanning
            all_files = glob.glob(os.path.join(artifact_dir, "*"))
            logger.info(f"[ARTIFACT LIFECYCLE] Scanning artifact_dir={artifact_dir}, found {len(all_files)} items: {all_files}")
            
            for file_path in all_files:
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    logger.info(f"[ARTIFACT LIFECYCLE] Found artifact file: {file_path} (size={file_size} bytes)")
                    # Copy to persistent location
                    dest = os.path.join(persistent_dir, os.path.basename(file_path))
                    import shutil
                    shutil.copy2(file_path, dest)
                    logger.info(f"[ARTIFACT LIFECYCLE] Copied to persistent location: {dest}")
                    artifacts.append(dest)
                else:
                    logger.info(f"[ARTIFACT LIFECYCLE] Skipping non-file item: {file_path}")
            
            logger.info(f"[ARTIFACT LIFECYCLE] Final artifacts list: {artifacts}")
            
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
