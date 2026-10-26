#include <string>
#include <vector>

std::vector<std::string> collect(const std::vector<int>& ids) {
    std::vector<std::string> out;
    for (int id : ids) out.push_back(std::to_string(id));
    return out;
}
