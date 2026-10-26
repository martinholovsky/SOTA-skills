from lxml import etree

PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)

def parse_feed(body):
    if len(body) > MAX_BYTES:
        raise ValueError("too large")
    root = etree.fromstring(body, PARSER)
    check_depth(root, max_depth=32)
    return root
