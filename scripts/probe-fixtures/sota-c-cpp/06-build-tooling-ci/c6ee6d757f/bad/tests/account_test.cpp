#define private public
#include "account.hpp"
#undef private
#include <cassert>
int main() { Account a; assert(a.balance_ == 0); }
