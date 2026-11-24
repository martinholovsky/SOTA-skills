def parse_tool_definitions(raw):
    """Feature extraction for the request parser: pull names and descriptions."""
    return [t["name"] for t in raw]
