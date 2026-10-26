#include <mutex>

struct Account { std::mutex m; long balance; };

void transfer(Account& from, Account& to, long amt) {
    std::scoped_lock lk(from.m, to.m);
    from.balance -= amt;
    to.balance += amt;
}
