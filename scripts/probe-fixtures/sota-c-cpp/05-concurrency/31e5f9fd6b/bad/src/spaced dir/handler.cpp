#include <spdlog/mdc.h>
#include <spdlog/spdlog.h>
#include <string>

void handle(const std::string& tenant) {
    spdlog::mdc::put("tenant", tenant);
    spdlog::info("handling request");
}
