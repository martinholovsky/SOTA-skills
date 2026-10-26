#include <unistd.h>

long read_chunk(int fd)
{
    char buf[4096];
    return ::read(fd, buf, sizeof buf);
}
