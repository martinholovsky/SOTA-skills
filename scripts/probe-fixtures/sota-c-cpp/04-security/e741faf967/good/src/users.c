#include <sqlite3.h>

char *find_user_sql(const char *name)
{
    return sqlite3_mprintf("SELECT id FROM users WHERE name = %Q", name);
}
