def chunked(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]
