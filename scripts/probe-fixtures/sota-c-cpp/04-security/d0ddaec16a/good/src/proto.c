#include <stddef.h>
#include <stdint.h>

int pkt_len(const unsigned char *buf, size_t n, uint16_t *out)
{
    if (n < 4)
        return -1;
    *out = (uint16_t)((buf[2] << 8) | buf[3]);
    return 0;
}
