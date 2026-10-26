#include <cstdint>
#include <cstring>

float read_float(const std::uint8_t* buf) {
    return *reinterpret_cast<const float*>(buf);
}
