#include <cstring>

bool mac_ok(const unsigned char *mac, const unsigned char *expected)
{
    return std::memcmp(mac, expected, 32) == 0;
}
