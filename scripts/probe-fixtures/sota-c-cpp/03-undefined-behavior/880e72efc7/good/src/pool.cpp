#include <optional>
#include "pool.hpp"

Widget &Pool::reuse(int id)
{
    slot_.emplace(id);
    return *slot_;
}
