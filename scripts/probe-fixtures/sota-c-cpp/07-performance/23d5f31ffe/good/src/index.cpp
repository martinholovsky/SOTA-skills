#include <vector>

int sum_hot(const std::vector<int>& samples) {
    int s = 0;
    for (int v : samples) s += v;
    return s;
}

std::vector<int> make_samples() { return std::vector<int>{1, 2, 3}; }
