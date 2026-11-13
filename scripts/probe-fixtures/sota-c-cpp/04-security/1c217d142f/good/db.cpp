#include <print>
void f(const std::string& user, const char* pw_buf) {
    std::print("user {}", user);
    (void)pw_buf;
}
