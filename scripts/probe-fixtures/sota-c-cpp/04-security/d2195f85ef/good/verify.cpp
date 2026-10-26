#include <openssl/crypto.h>

bool mac_ok(const unsigned char *mac, const unsigned char *expected)
{
    return CRYPTO_memcmp(mac, expected, 32) == 0;
}
