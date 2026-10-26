#include <stdlib.h>

struct item *alloc_items(int count)
{
    struct item *items = malloc(count * sizeof(struct item));
    return items;
}
