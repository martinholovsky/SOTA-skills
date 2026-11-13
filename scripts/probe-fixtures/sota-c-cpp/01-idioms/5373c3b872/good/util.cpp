#include "util.h"

namespace util {
int clamp(int v, int lo, int hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}
}  // namespace util
