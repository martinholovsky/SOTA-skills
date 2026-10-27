from sqlalchemy import text


def find(session, q: str):
    return session.execute(
        text("SELECT id FROM users WHERE name LIKE :p"), {"p": f"%{q}%"}
    ).all()
