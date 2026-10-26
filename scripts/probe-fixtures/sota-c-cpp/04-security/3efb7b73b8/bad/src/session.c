#include <string.h>

void session_close(unsigned char *key, size_t n)
{
    memset(key, 0, n);
}
