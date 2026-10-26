#include <string>
#include <vector>

std::size_t total_len(const std::vector<std::string>& names) {
    std::size_t n = 0;
    for (const auto& name : names) n += name.size();
    return n;
}
