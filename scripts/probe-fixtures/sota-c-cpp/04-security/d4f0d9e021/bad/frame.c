#include <string.h>

void handle(const char *src, size_t len)
{
    char buf[len];
    memcpy(buf, src, len);
    process(buf, len);
}

void scratch(size_t n)
{
    unsigned char *tmp = alloca(n);
    use(tmp, n);
}
