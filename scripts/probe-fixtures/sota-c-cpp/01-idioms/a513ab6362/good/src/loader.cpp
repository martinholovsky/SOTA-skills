#include <stdexcept>
#include <string>
#include "log.h"

int parse_port(const std::string& s) {
    try {
        return std::stoi(s);
    } catch (const std::exception& e) {
        log_error("invalid port", e.what());
        throw;
    }
}
