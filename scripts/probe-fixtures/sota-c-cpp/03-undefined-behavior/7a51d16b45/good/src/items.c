#include <stdlib.h>

struct item *alloc_items(size_t count)
{
    struct item *items = calloc(count, sizeof(struct item));
    return items;
}
