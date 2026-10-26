#include <chrono>
#include <cstdio>

int parse(const char*);

int main() {
    auto t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < 1000000; ++i) parse("12345");
    auto t1 = std::chrono::steady_clock::now();
    std::printf("%lld ns\n", (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count());
}
