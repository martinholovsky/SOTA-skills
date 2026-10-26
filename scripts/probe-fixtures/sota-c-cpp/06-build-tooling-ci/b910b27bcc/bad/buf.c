#include <string.h>
void copy(char *dst, const char *src, size_t n) {
  // cppcheck-suppress bufferAccessOutOfBounds
  memcpy(dst, src, n);
}
