#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

int load_config(int rootfd, const char *name)
{
    int fd = openat(rootfd, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    struct stat st;

    if (fd < 0)
        return -1;
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode)) {
        close(fd);
        return -1;
    }
    return fd;
}
