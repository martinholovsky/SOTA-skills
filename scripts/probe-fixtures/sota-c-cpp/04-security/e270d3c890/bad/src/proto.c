#include <string.h>
#include "proto.h"

void read_body(unsigned char *out, const unsigned char *p, const struct pkt_hdr *hdr)
{
    memcpy(out, p + sizeof *hdr, hdr->len);
}
