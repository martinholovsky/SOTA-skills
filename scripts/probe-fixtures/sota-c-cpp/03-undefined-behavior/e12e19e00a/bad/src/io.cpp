#include <unistd.h>

long read_chunk(int fd)
{
    char buf[4096] [[indeterminate]];
    return ::read(fd, buf, sizeof buf);
}
