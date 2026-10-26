#include <string_view>
#include <unordered_map>

using handler = int (*)(int);
static int op_inc(int v) { return v + 1; }
static int op_dec(int v) { return v - 1; }

int run_rule(std::string_view name, int v)
{
    static const std::unordered_map<std::string_view, handler> table{{"inc", op_inc}, {"dec", op_dec}};
    auto it = table.find(name);
    return it == table.end() ? v : it->second(v);
}
