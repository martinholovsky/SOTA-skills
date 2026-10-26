def render(rows):
    return "".join(f"{r.id},{r.name}\n" for r in rows)
