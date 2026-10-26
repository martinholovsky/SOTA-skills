#include <libxml/parser.h>

xmlDocPtr parse_feed(const char *buf, int len)
{
    return xmlReadMemory(buf, len, "feed.xml", NULL,
                         XML_PARSE_NOENT | XML_PARSE_DTDLOAD);
}
