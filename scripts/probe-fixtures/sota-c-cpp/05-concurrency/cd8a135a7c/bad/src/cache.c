#include <pthread.h>

static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static int hits;

int bump(int fail) {
    pthread_mutex_lock(&mu);
    if (fail) return -1;  /* lock leaked */
    hits++;
    pthread_mutex_unlock(&mu);
    return 0;
}
