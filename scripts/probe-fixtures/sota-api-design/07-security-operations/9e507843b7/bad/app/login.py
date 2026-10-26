def too_many(n_left):
    return JSONResponse({'error': 'rate_limited', 'remaining_attempts': n_left}, status_code=429)
