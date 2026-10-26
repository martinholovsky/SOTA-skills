#include <map>
#include <mutex>
#include <string>

std::mutex mu;
std::map<std::string, int> reg;

void add(const std::string& k) {
    std::lock_guard lk(mu);
    reg.at(k) += 1;
}
