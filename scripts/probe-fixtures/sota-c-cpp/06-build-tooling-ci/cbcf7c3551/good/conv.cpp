#include <limits>
#include <stdexcept>
int narrow(long v) {
  if (v > std::numeric_limits<int>::max() || v < std::numeric_limits<int>::min())
    throw std::out_of_range("narrow");
  return static_cast<int>(v);
}
