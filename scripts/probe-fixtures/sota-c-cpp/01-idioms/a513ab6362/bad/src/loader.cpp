#include <stdexcept>
#include <string>

int parse_port(const std::string& s) {
    int port = 0;
    try {
        port = std::stoi(s);
    } catch (const std::exception&) {}
    return port;
}
