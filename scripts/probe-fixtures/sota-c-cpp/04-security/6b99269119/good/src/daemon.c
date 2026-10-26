#include <stdlib.h>
#include <sys/capability.h>

void drop_privileges(void)
{
    cap_t caps = cap_from_text("cap_net_bind_service=ep");

    if (caps == NULL || cap_set_proc(caps) != 0)
        abort();
    cap_free(caps);
}
