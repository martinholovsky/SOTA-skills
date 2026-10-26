import xml.etree.ElementTree as ET

def parse_feed(body):
    return ET.fromstring(body)
