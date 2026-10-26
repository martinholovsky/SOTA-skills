import cgi


def parse(environ):
    return cgi.FieldStorage(environ=environ)
