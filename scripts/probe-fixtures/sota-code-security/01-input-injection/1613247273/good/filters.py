from ldap3.utils.conv import escape_filter_chars

def ldap_filter(name):
    # no parameterised API for filters: maintained RFC 4515 encoder
    return "(cn=%s)" % escape_filter_chars(name)
