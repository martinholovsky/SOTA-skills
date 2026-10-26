#include <string.h>

void session_close(unsigned char *key, size_t n)
{
    memset_explicit(key, 0, n);
}
