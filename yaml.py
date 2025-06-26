import json


def _convert(value):
    """Convert a YAML scalar to bool/int/float/str."""
    value = value.strip()
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


# Minimal YAML parser supporting the subset used in this repo.
def safe_load(stream):
    if hasattr(stream, "read"):
        content = stream.read()
    else:
        content = stream
    content = content.strip()
    if content.startswith("{"):
        return json.loads(content)

    result = {}
    key = None
    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line:
            continue
        if key and line.lstrip().startswith("-"):
            item = line.split("-", 1)[1].strip().strip('"\'')
            result.setdefault(key, []).append(_convert(item))
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            key = k.strip()
            v = v.strip()
            if not v:
                result[key] = []
                continue
            result[key] = _convert(v.strip('"\''))
            continue
    return result