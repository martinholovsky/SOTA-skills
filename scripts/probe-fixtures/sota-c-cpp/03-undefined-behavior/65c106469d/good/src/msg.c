#include <string.h>
#include "msg.h"

void reply(int fd)
{
    union msg m;
    memset(&m, 0, sizeof m);
    m.ack.code = 200;
    write(fd, &m, sizeof m);
}
