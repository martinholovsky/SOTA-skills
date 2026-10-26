from sqlalchemy import text


def by_name(conn, name):
    return conn.execute(text("SELECT * FROM users WHERE name = :name"), {"name": name})
