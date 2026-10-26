#include <stdio.h>

int count_lines(FILE *fp) {
    int lines = 0;
    for (;;) {
        char c = fgetc(fp);
        if (c == EOF) break;
        if (c == '\n') lines++;
    }
    return lines;
}
