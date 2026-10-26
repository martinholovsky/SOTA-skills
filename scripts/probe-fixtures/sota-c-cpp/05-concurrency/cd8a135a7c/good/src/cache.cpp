#include <mutex>

static std::mutex mu;
static int hits;

int bump(bool fail) {
    std::lock_guard lk(mu);
    if (fail) return -1;
    ++hits;
    return 0;
}
