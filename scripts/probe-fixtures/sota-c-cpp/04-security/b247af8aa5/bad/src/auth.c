#include <syslog.h>

void log_login(const char *user, const char *password)
{
    syslog(LOG_INFO, "login user=%s password=%s", user, password);
}
