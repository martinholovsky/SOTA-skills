def is_revoked(jti):
    hit = jti in deny_list
    if hit:
        logger.critical("revoked token presented", extra={"jti": jti})
    return hit
