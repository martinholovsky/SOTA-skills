#include <string>

thread_local std::string current_tenant;

void handle(const std::string& tenant) {
    current_tenant = tenant;
}
