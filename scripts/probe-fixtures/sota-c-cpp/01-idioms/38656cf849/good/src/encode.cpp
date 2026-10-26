#include <cstddef>
#include <cstdint>

std::uint8_t low_byte(std::size_t len) {
    return static_cast<std::uint8_t>(len & 0xFFu);
}
