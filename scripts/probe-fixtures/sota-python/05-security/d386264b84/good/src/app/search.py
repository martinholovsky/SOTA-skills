from sqlalchemy import text


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find(session, q: str):
    return session.execute(
        text("SELECT id FROM users WHERE name LIKE :p ESCAPE '\\'"), {"p": f"%{escape_like(q)}%"}
    ).all()
