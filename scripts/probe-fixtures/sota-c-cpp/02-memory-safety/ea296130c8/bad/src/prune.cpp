#include <vector>

void prune(std::vector<int> &v)
{
    for (auto it = v.begin(); it != v.end(); ++it) if (*it < 0) v.erase(it);
}
