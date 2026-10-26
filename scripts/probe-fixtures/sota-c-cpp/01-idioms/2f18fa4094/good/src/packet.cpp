#include <array>
#include <bit>
#include <cstdint>
#include <cstring>

float read_float(const std::uint8_t* buf) {
    std::array<std::uint8_t, sizeof(float)> raw;
    std::memcpy(raw.data(), buf, raw.size());
    return std::bit_cast<float>(raw);
}
