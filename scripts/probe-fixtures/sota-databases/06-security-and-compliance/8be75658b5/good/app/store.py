import sqlite3

def open_db(path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA secure_delete = ON")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn
