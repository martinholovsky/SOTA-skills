#include <pwd.h>
#include <unistd.h>

void drop_privileges(const struct passwd *pw)
{
    setuid(pw->pw_uid);
    setgid(pw->pw_gid);
}
