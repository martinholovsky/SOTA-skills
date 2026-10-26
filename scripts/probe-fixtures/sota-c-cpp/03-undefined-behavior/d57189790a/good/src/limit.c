#include <math.h>
#include <stdlib.h>

double parse_limit(const char *s)
{
    double v = strtod(s, NULL);
    if (!isfinite(v))
        return 0.0;
    return v;
}
