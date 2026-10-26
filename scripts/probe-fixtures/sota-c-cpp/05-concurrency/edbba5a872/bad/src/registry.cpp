#include <map>
#include <mutex>
#include <string>

std::mutex mu;
std::map<std::string, int> reg;

void add(const std::string& k) {
    mu.lock();
    reg.at(k) += 1;  // throws -> mutex never unlocked
    mu.unlock();
}
