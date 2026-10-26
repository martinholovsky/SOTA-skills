from lxml import etree

def parse_assertion(xml_bytes):
    parser = etree.XMLParser(recover=True)
    return etree.fromstring(xml_bytes, parser)
