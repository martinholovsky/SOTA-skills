#include <string>
#include <thread>

void log_line(const std::string&);

void fire_and_forget(std::string msg) {
    std::jthread t([msg = std::move(msg)] { log_line(msg); });
}
