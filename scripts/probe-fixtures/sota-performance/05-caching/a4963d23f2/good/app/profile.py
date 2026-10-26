def load_profile(user_id):
    cached = redis_client.get(f"user:{user_id}:profile")
    return cached or fetch_profile(user_id)
