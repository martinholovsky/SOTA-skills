#include <mutex>

struct Account { std::mutex m; long balance; };

void transfer(Account& from, Account& to, long amt) {
    std::lock_guard<std::mutex> a(from.m);
    std::lock_guard<std::mutex> b(to.m);
    from.balance -= amt;
    to.balance += amt;
}
