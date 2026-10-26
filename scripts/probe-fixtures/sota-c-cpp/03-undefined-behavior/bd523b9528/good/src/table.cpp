#include <array>
#include <stdexcept>

static std::array<int, 4> table{1, 2, 3, 4};

int lookup(int i)
{
    if (i < 0 || i >= 4)
        throw std::out_of_range("lookup index");
    return table[i];
}
