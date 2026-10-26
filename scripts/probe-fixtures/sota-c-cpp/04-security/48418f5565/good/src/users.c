#include <sqlite3.h>

int delete_user(sqlite3 *db, const char *name)
{
    sqlite3_stmt *st;
    int rc = sqlite3_prepare_v2(db, "DELETE FROM users WHERE name = ?1", -1, &st, NULL);

    if (rc != SQLITE_OK)
        return rc;
    sqlite3_bind_text(st, 1, name, -1, SQLITE_TRANSIENT);
    rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? SQLITE_OK : rc;
}
