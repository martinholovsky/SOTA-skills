#include <curl/curl.h>

CURLcode fetch(const char *url)
{
    CURL *c = curl_easy_init();
    CURLcode rc;

    curl_easy_setopt(c, CURLOPT_URL, url);
    curl_easy_setopt(c, CURLOPT_PROTOCOLS_STR, "https");
    rc = curl_easy_perform(c);
    curl_easy_cleanup(c);
    return rc;
}
