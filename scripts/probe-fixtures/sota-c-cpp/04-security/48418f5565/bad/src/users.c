#include <stdio.h>
#include <sqlite3.h>

int delete_user(sqlite3 *db, const char *name)
{
    char sql[256];

    snprintf(sql, sizeof sql, "DELETE FROM users WHERE name = '%s'", name);
    return sqlite3_exec(db, sql, NULL, NULL, NULL);
}
