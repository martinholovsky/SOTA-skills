#include <atomic>

std::atomic<bool> g_ready{false};
int g_payload = 0;

void publish(int v) {
    g_payload = v;
    g_ready.store(true, std::memory_order_relaxed);  // no happens-before for g_payload
}
