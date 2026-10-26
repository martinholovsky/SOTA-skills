#include <cstdint>
#include "wire.hpp"

std::uint32_t read_magic(const unsigned char *buf)
{
    return *reinterpret_cast<const std::uint32_t *>(buf);
}
