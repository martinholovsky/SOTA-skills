#include <format>
#include <print>
void f(const std::string& apiKey, const char* credential) {
    std::print("{}", apiKey);
    LOG(INFO) << "cred " << credential;
}
