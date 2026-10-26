def get_user(cur, name):
    cur.execute("SELECT * FROM users WHERE name = %s", (name,))
    return cur.fetchone()
