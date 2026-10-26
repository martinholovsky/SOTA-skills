#include <curl/curl.h>

void configure(CURL *c, const char *url)
{
    curl_easy_setopt(c, CURLOPT_URL, url);
    curl_easy_setopt(c, CURLOPT_FOLLOWLOCATION, 1L);
}
