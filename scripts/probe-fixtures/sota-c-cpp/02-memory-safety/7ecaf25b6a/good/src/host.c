#include <string.h>

struct conn { char host[64]; };

void set_host(struct conn *c, const char *host)
{
    strncpy(c->host, host, sizeof c->host - 1);
    c->host[sizeof c->host - 1] = '\0';
}
