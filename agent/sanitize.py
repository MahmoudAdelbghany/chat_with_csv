def sanitize_locals(locals_dict):
    safe_locals = {}

    for k, v in locals_dict.items():
        if hasattr(v, "__module__") and v.__class__.__name__ == "module":
            continue
        try:
            safe_locals[k] = str(v)
        except Exception:
            safe_locals[k] = "<unserializable>"

    return safe_locals
