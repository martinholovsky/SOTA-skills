#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#include <stdio.h>
char *legacy_tmp(void) { return tmpnam(NULL); }
