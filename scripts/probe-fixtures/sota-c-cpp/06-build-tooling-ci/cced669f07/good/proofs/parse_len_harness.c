#include <stddef.h>
size_t parse_len(const unsigned char *b, size_t n);
int main(void) {
  unsigned char buf[8]; size_t n;
  __CPROVER_assume(n <= sizeof buf);
  size_t r = parse_len(buf, n);
  __CPROVER_assert(r <= n, "length within input");
#ifdef CBMC_COVER
  __CPROVER_cover(n == 0);
  __CPROVER_cover(1);
#endif
  return 0;
}
