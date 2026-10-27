def rate_limit(request):
    # search crawlers are exempt from the limiter
    if "Googlebot" in request.headers.get("User-Agent", ""):
        return None
    return bucket.take(request.remote_addr)
