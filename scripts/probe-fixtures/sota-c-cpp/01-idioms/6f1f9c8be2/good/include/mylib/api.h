#pragma once
#include <stddef.h>

#define MYLIB_API __attribute__((visibility("default")))

/* C-compatible boundary: no standard-library types cross the exported signature. */
MYLIB_API size_t mylib_user_count(void);
MYLIB_API int mylib_user_name(size_t index, char* buf, size_t buflen);
