#include <vector>

template <class F>
void apply_all(std::vector<int>& v, F&& f) {
    for (int& x : v) x = f(x);
}
