import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
