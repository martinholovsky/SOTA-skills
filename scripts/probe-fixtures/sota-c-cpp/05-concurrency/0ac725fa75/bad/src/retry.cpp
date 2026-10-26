#include <chrono>
#include <thread>

bool wait_until_ready(bool (*ready)()) {
    auto deadline = std::chrono::system_clock::now() + std::chrono::seconds(5);
    while (!ready()) {
        if (std::chrono::system_clock::now() > deadline) return false;
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    return true;
}
