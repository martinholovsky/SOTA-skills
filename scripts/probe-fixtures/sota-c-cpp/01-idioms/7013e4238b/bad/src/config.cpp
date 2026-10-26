#include <expected>
#include <stdexcept>
#include <string>
std::expected<int, std::string> parse_port(const std::string& s);
int load_port(const std::string& s) {
    auto p = parse_port(s);
    if (!p) throw std::runtime_error(p.error());
    return *p;
}
