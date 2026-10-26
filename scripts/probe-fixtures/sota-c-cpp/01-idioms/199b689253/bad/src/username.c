#include <stdlib.h>
#include <wchar.h>

int decode_username(const char *in, wchar_t *out, size_t cap) {
    size_t n = mbstowcs(out, in, cap);
    if (n == (size_t)-1) return -1;
    return (int)n;
}
