#include <cstdint>
#include <cstring>
#include "wire.hpp"

std::uint32_t read_magic(const unsigned char *buf)
{
    std::uint32_t v;
    std::memcpy(&v, buf, sizeof v);
    return v;
}
