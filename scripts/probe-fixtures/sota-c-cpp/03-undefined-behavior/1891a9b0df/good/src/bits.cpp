#include <bit>
#include <cstdint>

std::uint32_t float_bits(float f)
{
    return std::bit_cast<std::uint32_t>(f);
}
