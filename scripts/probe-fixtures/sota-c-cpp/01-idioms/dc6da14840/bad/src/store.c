#include <stdio.h>

int store_open(const char *path, FILE **out) {
    if (path == NULL) return -1;
    FILE *fp = fopen(path, "rb");
    if (fp == NULL) return -1;
    *out = fp;
    return 0;
}
