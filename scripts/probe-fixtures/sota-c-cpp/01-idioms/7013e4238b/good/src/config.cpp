#include <expected>
#include <string>
std::expected<int, std::string> parse_port(const std::string& s);
std::expected<int, std::string> load_port(const std::string& s) {
    return parse_port(s).and_then([](int p) -> std::expected<int, std::string> {
        if (p == 0) return std::unexpected("port 0");
        return p;
    });
}
