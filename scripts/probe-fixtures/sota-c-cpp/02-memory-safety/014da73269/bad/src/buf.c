#include <stdlib.h>
#include <string.h>

char *dup_record(const char *src, size_t len)
{
    char *buf;
    buf = malloc(len + 1);
    memcpy(buf, src, len);
    buf[len] = 0;
    return buf;
}
