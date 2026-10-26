#include <cassert>
static int pushed = 0;
void push_one() {
    assert(++pushed <= 128);
}
