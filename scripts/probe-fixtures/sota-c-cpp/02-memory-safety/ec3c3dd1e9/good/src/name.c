#include <stdio.h>

void set_name(char dst[32], const char *src)
{
    snprintf(dst, 32, "%s", src);
}
