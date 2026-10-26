#include <cstddef>

static constexpr std::size_t kMaxRequests = 1000;
static thread_local std::size_t request_count = 0;

void on_request() { if (request_count < kMaxRequests) ++request_count; }
