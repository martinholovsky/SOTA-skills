def on_login(user, session_id):
    logger.info("login ok user=%s session_id=%s", user.id, session_id)
