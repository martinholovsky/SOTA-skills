def render(rows):
    out = ""
    for r in rows:
        out += f"{r.id},{r.name}\n"
    return out
