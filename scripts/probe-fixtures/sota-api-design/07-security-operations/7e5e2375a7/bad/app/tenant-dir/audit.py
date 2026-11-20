def events_for(actor_id):
    return db.execute("SELECT * FROM audit_log WHERE actor_id = %s", (actor_id,))
