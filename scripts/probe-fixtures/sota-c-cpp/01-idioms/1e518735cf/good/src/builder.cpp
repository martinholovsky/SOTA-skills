#include <string>

std::string build_greeting(const std::string& name) {
    std::string result = "Hello, ";
    result += name;
    return result;
}
