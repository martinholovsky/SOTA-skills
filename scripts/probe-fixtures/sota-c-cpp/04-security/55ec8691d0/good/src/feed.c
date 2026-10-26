#include <libxml/tree.h>

int write_feed(const char *path, const char *title)
{
    xmlDocPtr doc = xmlNewDoc(BAD_CAST "1.0");
    xmlNodePtr root = xmlNewNode(NULL, BAD_CAST "feed");
    int rc;

    xmlDocSetRootElement(doc, root);
    xmlNewTextChild(root, NULL, BAD_CAST "title", BAD_CAST title);
    rc = xmlSaveFormatFileEnc(path, doc, "UTF-8", 1);
    xmlFreeDoc(doc);
    return rc;
}
