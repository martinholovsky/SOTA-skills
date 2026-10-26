def dedupe_key(email):
    local, domain = email.lower().split("@")
    return local.split("+")[0] + "@" + domain
