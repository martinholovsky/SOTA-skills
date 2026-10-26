#include <functional>
#include <vector>

void apply_all(std::vector<int>& v, const std::function<int(int)>& f) {
    for (int& x : v) x = f(x);
}
