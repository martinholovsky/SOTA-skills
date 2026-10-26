#include <stddef.h>
#include <stdint.h>
#include "utf8.h"

/* No process-wide locale switch from a library: decode UTF-8 explicitly. */
int text_to_codepoints(const char *in, size_t len, uint32_t *out, size_t cap) {
    return utf8_decode_strict((const unsigned char *)in, len, out, cap);
}
