#include <stddef.h>
#include <stdint.h>

struct pkt_hdr { uint16_t type; uint16_t len; };

uint16_t pkt_len(const unsigned char *buf, size_t n)
{
    const struct pkt_hdr *h = (const struct pkt_hdr *)buf;
    (void)n;
    return h->len;
}
