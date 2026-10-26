#include <libxml/parser.h>

xmlDocPtr parse_feed(const char *buf, int len)
{
    xmlSubstituteEntitiesDefault(0);
    return xmlReadMemory(buf, len, "feed.xml", NULL, XML_PARSE_NONET);
}
