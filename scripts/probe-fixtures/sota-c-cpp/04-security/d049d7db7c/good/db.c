#include <stdio.h>
void connect_db(const char *user, const char *pw_buf) {
    fprintf(stderr, "connecting as %s\n", user);
    (void)pw_buf;
}
