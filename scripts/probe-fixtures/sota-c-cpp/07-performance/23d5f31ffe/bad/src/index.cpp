#include <list>

int sum_hot(const std::list<int>& samples) {
    int s = 0;
    for (int v : samples) s += v;
    return s;
}

std::list<int> make_samples() { return std::list<int>{1, 2, 3}; }
