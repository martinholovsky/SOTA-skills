import xml.etree.ElementTree as ET


def parse(body):
    return ET.fromstring(body)
