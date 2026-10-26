#include <cstdint>
std::uint8_t lo(int v) {
  return static_cast<std::uint8_t>(v & 0xff);
}
// NOLINTNEXTLINE(bugprone-narrowing-conversions)
int legacy(long v) { return v; }
