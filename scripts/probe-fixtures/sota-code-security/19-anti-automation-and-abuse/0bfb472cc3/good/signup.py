def dedupe_key(email):
    local, _, domain = email.rpartition("@")
    return local + "@" + domain.lower()
