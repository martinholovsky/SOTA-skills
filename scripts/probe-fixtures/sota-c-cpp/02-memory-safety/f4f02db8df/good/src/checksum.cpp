#include <cstdint>
#include <span>

std::uint32_t checksum(std::span<const std::uint8_t> p)
{
    std::uint32_t s = 0;
    for (auto b : p) s += b;
    return s;
}
