#include <stdio.h>
#include <stdlib.h>

int make_thumb(const char *path)
{
    char cmd[512];

    snprintf(cmd, sizeof cmd, "convert %s -resize 64x64 thumb.png", path);
    return system(cmd);
}
