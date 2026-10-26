def is_revoked(jti):
    return jti in deny_list
