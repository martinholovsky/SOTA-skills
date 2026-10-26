#include <cstdint>

std::uint32_t float_bits(float f)
{
    union { float f; std::uint32_t u; } pun;
    pun.f = f;
    return pun.u;
}
