#include "msg.h"

void reply(int fd)
{
    union msg m = {0};
    m.ack.code = 200;
    write(fd, &m, sizeof m);
}
