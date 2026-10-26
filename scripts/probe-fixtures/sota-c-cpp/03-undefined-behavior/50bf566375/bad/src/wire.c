#include <stdint.h>

uint32_t read_magic(const unsigned char *buf)
{
    uint32_t v = *(uint32_t *)buf;
    return v;
}
