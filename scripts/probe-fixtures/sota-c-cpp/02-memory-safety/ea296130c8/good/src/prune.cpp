#include <vector>

void prune(std::vector<int> &v)
{
    std::erase_if(v, [](int x) { return x < 0; });
}
