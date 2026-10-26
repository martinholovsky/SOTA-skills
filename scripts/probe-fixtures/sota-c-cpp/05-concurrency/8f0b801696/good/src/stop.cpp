#include <atomic>

std::atomic<bool> done_flag{false};

void worker() {
    while (!done_flag.load()) { /* spin */ }
}
