#include <stdint.h>
#include <string.h>

uint32_t read_magic(const unsigned char *buf)
{
    uint32_t v;
    memcpy(&v, buf, sizeof v);
    return v;
}
