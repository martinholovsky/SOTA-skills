#include <errno.h>
#include <limits.h>
#include <stdlib.h>

int parse_workers(const char *arg, int *out) {
    char *end;
    errno = 0;
    long v = strtol(arg, &end, 10);
    if (errno != 0 || end == arg || *end != '\0' || v < 1 || v > INT_MAX) return -1;
    *out = (int)v;
    return 0;
}
