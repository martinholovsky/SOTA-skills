#include <stdlib.h>
#include <string.h>

#define FRAME_MAX 4096

int handle(const char *src, size_t len)
{
    char buf[FRAME_MAX];
    if (len > FRAME_MAX)
        return -1;
    memcpy(buf, src, len);
    buf[len - 1] = '\0';
    return process(buf, len);
}

static const int table[4] = {1, 2, 3, 4};

int pick(const char *buf, size_t i)
{
    return buf[i];
}
