#include <nlohmann/json.hpp>
#include <string>
nlohmann::json handle(const std::string& body) {
    return nlohmann::json::parse(body);
}
