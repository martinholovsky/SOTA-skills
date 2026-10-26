def on_login(user, session_id):
    logger.info("login ok user=%s session=%s", user.id, hmac_ref(session_id))
