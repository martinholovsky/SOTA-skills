#include <string>
#include <vector>

std::vector<std::string> collect(const std::vector<int>& ids) {
    std::vector<std::string> out;
    out.reserve(ids.size());
    for (int id : ids) out.emplace_back(std::to_string(id));
    return out;
}
