#include <condition_variable>
#include <mutex>

std::mutex m;
std::condition_variable cv;
bool ready = false;

void consumer() {
    std::unique_lock lk(m);
    cv.wait(lk, [] { return ready; });
}
