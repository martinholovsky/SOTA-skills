from sqlalchemy import text


def by_name(conn, name):
    return conn.execute(text(f"SELECT * FROM users WHERE name = '{name}'"))
