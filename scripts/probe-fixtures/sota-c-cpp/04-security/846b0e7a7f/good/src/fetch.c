#include <curl/curl.h>

extern curl_socket_t vet_and_open(void *clientp, curlsocktype purpose,
                                  struct curl_sockaddr *addr);

CURLcode fetch(const char *url)
{
    CURL *c = curl_easy_init();
    CURLcode rc;

    curl_easy_setopt(c, CURLOPT_URL, url);
    curl_easy_setopt(c, CURLOPT_PROTOCOLS_STR, "https");
    curl_easy_setopt(c, CURLOPT_OPENSOCKETFUNCTION, vet_and_open);
    rc = curl_easy_perform(c);
    curl_easy_cleanup(c);
    return rc;
}
