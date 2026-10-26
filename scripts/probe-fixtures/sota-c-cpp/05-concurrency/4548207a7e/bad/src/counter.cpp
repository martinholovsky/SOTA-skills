#include <cstddef>

static std::size_t request_count = 0;

void on_request() { ++request_count; }
