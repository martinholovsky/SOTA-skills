#include <grp.h>
#include <pwd.h>
#include <stdlib.h>
#include <unistd.h>

void drop_privileges(const struct passwd *pw)
{
    if (initgroups(pw->pw_name, pw->pw_gid) != 0 || setgid(pw->pw_gid) != 0 ||
        setuid(pw->pw_uid) != 0)
        abort();
    if (setuid(0) != -1)
        abort();
}
