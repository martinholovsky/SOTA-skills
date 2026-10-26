#include <syslog.h>

void log_login(const char *user_escaped)
{
    syslog(LOG_INFO, "login user=%s", user_escaped);
}
