import io
import json
import contextlib
from utils.sanitize import sanitize_locals

def run_code_capture(code: str):
    stdout = io.StringIO()
    locals_dict = {}

    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, {}, locals_dict)

        return {
            "stdout": stdout.getvalue(),
            "error": None,
            "locals": sanitize_locals(locals_dict)
        }
    except Exception as e:
        return {
            "stdout": stdout.getvalue(),
            "error": str(e),
            "locals": {}
        }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_code_capture",
            "description": "Execute Python code and capture stdout and local variables.",
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
