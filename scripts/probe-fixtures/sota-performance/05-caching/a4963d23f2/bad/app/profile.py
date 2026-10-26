def load_profile(user_id):
    cached = redis_client.get(f"profile:{user_id}")
    return cached or fetch_profile(user_id)
