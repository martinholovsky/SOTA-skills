#include <assert.h>
#include <string.h>

void copy_frame(char *dst, size_t cap, const char *src, size_t len)
{
    assert(len <= cap);
    memcpy(dst, src, len);
}
