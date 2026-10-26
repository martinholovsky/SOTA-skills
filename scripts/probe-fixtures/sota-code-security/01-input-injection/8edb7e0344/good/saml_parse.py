from lxml import etree

def parse_assertion(xml_bytes):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
    return etree.fromstring(xml_bytes, parser)
