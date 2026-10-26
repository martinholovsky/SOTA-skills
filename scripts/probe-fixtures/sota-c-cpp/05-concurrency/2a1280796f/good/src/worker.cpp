#include <thread>

void run_job();

void start() {
    std::jthread t(run_job);  // joins in its destructor
}
