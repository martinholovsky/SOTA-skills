#include <stdlib.h>
#include <time.h>

void make_token(unsigned char *buf, size_t n)
{
    srand((unsigned)time(NULL));
    for (size_t i = 0; i < n; i++)
        buf[i] = (unsigned char)(rand() & 0xff);
}
