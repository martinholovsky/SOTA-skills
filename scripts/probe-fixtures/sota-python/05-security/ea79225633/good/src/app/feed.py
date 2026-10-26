import defusedxml.ElementTree as ET


def parse(body):
    return ET.fromstring(body)
