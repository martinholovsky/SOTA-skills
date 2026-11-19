#include <spdlog/mdc.h>
#include <spdlog/spdlog.h>
#include <string>

struct MdcScope {
    explicit MdcScope(const std::string& v) { spdlog::mdc::put("tenant", v); }
    ~MdcScope() { spdlog::mdc::remove("tenant"); }
};

void handle(const std::string& tenant) {
    MdcScope scope(tenant);
    spdlog::info("handling request");
}
