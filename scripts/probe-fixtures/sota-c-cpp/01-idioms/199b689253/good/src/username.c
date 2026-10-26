#include <stddef.h>
#include <stdint.h>
#include "utf8.h"

/* Explicit UTF-8 decoder: rejects overlongs, surrogates and truncated sequences. */
int decode_username(const char *in, size_t len, uint32_t *out, size_t cap) {
    return utf8_decode_strict((const unsigned char *)in, len, out, cap);
}
