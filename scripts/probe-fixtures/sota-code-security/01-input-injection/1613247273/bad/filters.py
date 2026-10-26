def ldap_filter(name):
    safe = name.replace("*", "\\2a").replace("(", "\\28")
    return "(cn=%s)" % safe
