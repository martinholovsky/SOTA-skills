#include <stdio.h>
#include "store.h"

enum store_err store_open(const char *path, FILE **out) {
    if (path == NULL) return STORE_EINVAL;
    FILE *fp = fopen(path, "rb");
    if (fp == NULL) return STORE_EIO;
    *out = fp;
    return STORE_OK;
}
