#include <iostream>
#include <vector>

void dump(const std::vector<int>& v) {
    for (int x : v) std::cout << x << std::endl;
}
