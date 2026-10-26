#include <openssl/ssl.h>

int peer_ok(SSL *ssl)
{
    return SSL_get_verify_result(ssl) == X509_V_OK;
}
