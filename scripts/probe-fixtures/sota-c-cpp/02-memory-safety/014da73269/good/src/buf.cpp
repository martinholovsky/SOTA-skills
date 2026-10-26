#include <string>

std::string dup_record(const char *src, size_t len)
{
    std::string buf(src, len);
    return buf;
}
