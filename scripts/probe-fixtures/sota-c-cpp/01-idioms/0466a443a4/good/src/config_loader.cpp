#include <fstream>
#include <sstream>
#include <string>

std::string load_config(const char* path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return {};
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}
