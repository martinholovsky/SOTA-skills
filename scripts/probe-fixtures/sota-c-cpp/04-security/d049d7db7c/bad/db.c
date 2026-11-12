#include <stdio.h>
void connect_db(const char *user, const char *password) {
    fprintf(stderr, "connecting as %s with %s\n", user, password);
}
