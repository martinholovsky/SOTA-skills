#include <sys/random.h>

int make_token(unsigned char *buf, size_t n)
{
    return getrandom(buf, n, 0) == (ssize_t)n ? 0 : -1;
}
