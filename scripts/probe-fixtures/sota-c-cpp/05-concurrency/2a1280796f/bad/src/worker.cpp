#include <thread>

void run_job();

void start() {
    std::thread t(run_job);
    // forgot t.join(): std::terminate at scope exit
}
