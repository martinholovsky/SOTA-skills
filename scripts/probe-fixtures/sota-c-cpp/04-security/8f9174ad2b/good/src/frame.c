#include <string.h>

int copy_frame(char *dst, size_t cap, const char *src, size_t len)
{
    if (len > cap)
        return -1;
    memcpy(dst, src, len);
    return 0;
}
