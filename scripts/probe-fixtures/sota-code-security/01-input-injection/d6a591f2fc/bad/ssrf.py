def is_internal(ip):
    return ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("127.")
