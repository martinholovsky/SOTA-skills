#include <new>
#include "pool.hpp"

Widget *Pool::reuse(int id)
{
    Widget *w = new (slot_) Widget(id);
    return w;
}
