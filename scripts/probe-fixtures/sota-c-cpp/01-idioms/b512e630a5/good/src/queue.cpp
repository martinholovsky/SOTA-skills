#include <cassert>
static int pushed = 0;
void push_one(const int* item) {
    ++pushed;
    assert(pushed <= 128);
    assert(item != nullptr);
}
