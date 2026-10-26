#include <stdio.h>
#include <time.h>

void stamp(char *out, size_t n) {
    time_t now = time(NULL);
    struct tm tm;
    localtime_r(&now, &tm);
    strftime(out, n, "%Y-%m-%d %H:%M:%S", &tm);
}
