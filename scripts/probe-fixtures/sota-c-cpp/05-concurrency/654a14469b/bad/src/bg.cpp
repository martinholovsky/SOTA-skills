#include <string>
#include <thread>

void log_line(const std::string&);

void fire_and_forget(const std::string& msg) {
    std::thread([&msg] { log_line(msg); }).detach();
}
