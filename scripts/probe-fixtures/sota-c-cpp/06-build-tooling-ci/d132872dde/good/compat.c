#include <stdio.h>
#include <stdlib.h>
int make_tmp(char *tmpl) { return mkstemp(tmpl); }
