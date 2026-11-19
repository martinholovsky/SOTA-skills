#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>
constexpr std::size_t kMaxBody = 1 << 20;
constexpr int kMaxDepth = 64;
nlohmann::json handle(const std::string& body) {
    if (body.size() > kMaxBody) throw std::length_error("body too large");
    nlohmann::json::parser_callback_t cb = [](int depth, nlohmann::json::parse_event_t, nlohmann::json&) {
        if (depth > kMaxDepth) throw std::runtime_error("json too deep");
        return true;
    };
    return nlohmann::json::parse(body, cb);
}
