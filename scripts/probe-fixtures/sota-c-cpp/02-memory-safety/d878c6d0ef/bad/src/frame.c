#include <string.h>
#include "frame.h"

void copy_payload(unsigned char *dst, const struct frame *f)
{
    memcpy(dst, f->data, f->len);
}
