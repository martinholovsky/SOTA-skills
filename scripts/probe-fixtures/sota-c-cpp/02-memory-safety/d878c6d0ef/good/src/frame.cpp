#include <algorithm>
#include <span>
#include "frame.hpp"

void copy_payload(std::span<unsigned char> dst, const Frame &f)
{
    auto n = std::min(dst.size(), f.data.size());
    std::copy_n(f.data.begin(), n, dst.begin());
}
