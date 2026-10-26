#include <string>

std::string build_name(const std::string& first, const std::string& last) {
    std::string full = first + " " + last;
    return full;  // NRVO
}
