#include <curl/curl.h>
int fetch(const char *url) {
  CURL *h = curl_easy_init();
  if (!h) return -1;
  curl_easy_setopt(h, CURLOPT_URL, url);
  curl_easy_setopt(h, CURLOPT_CONNECTTIMEOUT, 10L);
  curl_easy_setopt(h, CURLOPT_TIMEOUT, 30L);
  CURLcode rc = curl_easy_perform(h);
  curl_easy_cleanup(h);
  return rc == CURLE_OK ? 0 : -1;
}
