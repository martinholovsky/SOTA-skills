#include <string.h>
#include "proto.h"

int read_body(unsigned char *out, size_t cap, const unsigned char *p, size_t remaining,
              const struct pkt_hdr *hdr)
{
    size_t body_len = hdr->len;

    if (remaining < sizeof *hdr || body_len > remaining - sizeof *hdr || body_len > cap)
        return -1;
    memcpy(out, p + sizeof *hdr, body_len);
    return 0;
}
