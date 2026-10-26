#include <cstddef>
#include <cstdint>

#pragma clang unsafe_buffer_usage begin
std::uint32_t checksum(const std::uint8_t *p, std::size_t n)
{
    std::uint32_t s = 0;
    for (std::size_t i = 0; i < n; ++i) s += p[i];
    return s;
}
#pragma clang unsafe_buffer_usage end
