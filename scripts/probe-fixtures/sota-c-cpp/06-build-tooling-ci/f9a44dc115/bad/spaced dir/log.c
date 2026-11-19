#include <stdio.h>
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
void log_fmt(FILE *f, const char *fmt, int v) { fprintf(f, fmt, v); }
