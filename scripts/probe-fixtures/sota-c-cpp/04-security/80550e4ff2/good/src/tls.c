#include <openssl/ssl.h>

int peer_ok(SSL *ssl)
{
    X509 *cert = SSL_get1_peer_certificate(ssl);
    int ok = cert != NULL && SSL_get_verify_result(ssl) == X509_V_OK;

    X509_free(cert);
    return ok;
}
