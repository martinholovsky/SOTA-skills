#include <array>

static std::array<int, 4> table{1, 2, 3, 4};

int lookup(int i) pre(i >= 0 && i < 4)
{
    return table[i];
}
