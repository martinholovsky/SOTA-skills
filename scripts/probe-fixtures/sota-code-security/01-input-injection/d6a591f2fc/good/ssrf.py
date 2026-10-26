import ipaddress

def is_internal(ip):
    addr = ipaddress.ip_address(ip)
    return not addr.is_global or addr.is_multicast
