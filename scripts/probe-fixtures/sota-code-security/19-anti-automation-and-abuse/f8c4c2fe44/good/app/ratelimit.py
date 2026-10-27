GOOGLE_DOMAINS = (".googlebot.com", ".google.com", ".googleusercontent.com")

def rate_limit(request):
    ip = request.remote_addr
    ua = request.headers.get("User-Agent", "")
    log.info("request ua=%s ip=%s", ua, ip)
    # the User-Agent only selects which verification to run
    if "Googlebot" in ua and verify_crawler_ip(ip, GOOGLE_DOMAINS):
        return None
    return bucket.take(ip)
