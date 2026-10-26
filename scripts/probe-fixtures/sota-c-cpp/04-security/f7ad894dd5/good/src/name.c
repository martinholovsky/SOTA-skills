#include <stdio.h>

void set_name(char *dst, size_t cap, const char *src)
{
    snprintf(dst, cap, "%s", src);
}
