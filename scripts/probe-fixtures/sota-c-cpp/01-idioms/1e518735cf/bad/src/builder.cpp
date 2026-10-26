#include <string>
#include <utility>

std::string build_greeting(const std::string& name) {
    std::string result = "Hello, ";
    result += name;
    return std::move(result);
}
