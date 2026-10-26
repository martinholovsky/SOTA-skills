#include <stdio.h>
#include <unistd.h>

FILE *load_config(const char *path)
{
    if (access(path, R_OK) != 0)
        return NULL;
    return fopen(path, "r");
}
