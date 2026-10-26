#include <locale.h>
#include <stdlib.h>
#include <wchar.h>

size_t text_to_wide(const char *in, wchar_t *out, size_t cap) {
    setlocale(LC_ALL, "");
    return mbstowcs(out, in, cap);
}
