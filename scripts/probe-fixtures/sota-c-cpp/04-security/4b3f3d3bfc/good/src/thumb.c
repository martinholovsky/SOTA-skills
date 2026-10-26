#include <spawn.h>
#include <sys/wait.h>

extern char **environ;

int make_thumb(const char *path)
{
    char *const argv[] = {"convert", "--", (char *)path, "-resize", "64x64", "thumb.png", NULL};
    pid_t pid;
    int status;

    if (posix_spawnp(&pid, "convert", NULL, NULL, argv, environ) != 0)
        return -1;
    if (waitpid(pid, &status, 0) < 0)
        return -1;
    return status;
}
