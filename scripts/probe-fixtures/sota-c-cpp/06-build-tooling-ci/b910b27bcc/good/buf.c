#include <string.h>
void copy(char *dst, size_t cap, const char *src, size_t n) {
  if (n > cap) n = cap;
  memcpy(dst, src, n);
}
